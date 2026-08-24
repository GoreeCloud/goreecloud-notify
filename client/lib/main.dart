import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'persistent_alerts.dart';

const _defaultServer = String.fromEnvironment(
  'GOREECLOUD_NOTIFY_URL',
  defaultValue: 'https://notify.goreecloud.com',
);
const _sessionCookieName = 'goreecloud_notify_session';
const _csrfHeader = 'X-CSRF-Token';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final alerts = ClientAlerts();
  await alerts.initialize();
  runApp(NotifyApp(api: NotifyApi(_defaultServer), alerts: alerts));
}

class Delivery {
  Delivery({
    required this.id,
    required this.source,
    required this.channel,
    required this.title,
    required this.body,
    required this.severity,
    required this.createdAt,
    required this.readAt,
    required this.acknowledgedAt,
  });

  final int id;
  final String source;
  final String channel;
  final String title;
  final String body;
  final String severity;
  final DateTime createdAt;
  final DateTime? readAt;
  final DateTime? acknowledgedAt;

  factory Delivery.fromJson(Map<String, dynamic> json) => Delivery(
        id: json['id'] as int,
        source: json['source'] as String,
        channel: json['channel'] as String,
        title: json['title'] as String,
        body: json['body'] as String,
        severity: json['severity'] as String,
        createdAt: DateTime.parse(json['notification_created_at'] as String).toLocal(),
        readAt: json['read_at'] == null ? null : DateTime.parse(json['read_at'] as String).toLocal(),
        acknowledgedAt: json['acknowledged_at'] == null
            ? null
            : DateTime.parse(json['acknowledged_at'] as String).toLocal(),
      );
}

class NotifyApi {
  NotifyApi(String server)
      : base = Uri.parse(server.endsWith('/') ? server.substring(0, server.length - 1) : server);

  final Uri base;
  final HttpClient _http = HttpClient();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _cookie;
  String? _csrf;

  String? get sessionCookie => _cookie;

  Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse('${base.toString()}$path');
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  Future<bool> restoreSession() async {
    _cookie = await _storage.read(key: 'session_cookie');
    _csrf = await _storage.read(key: 'csrf_token');
    if (_cookie == null) return false;
    try {
      final response = await _request('GET', '/api/v1/me');
      if (response.statusCode == 200) return true;
    } catch (_) {
      return false;
    }
    await clearSession();
    return false;
  }

  Future<void> login(String username, String password) async {
    final response = await _request(
      'POST',
      '/api/v1/session',
      jsonBody: {'username': username, 'password': password},
      authenticated: false,
    );
    if (response.statusCode != 200) {
      throw HttpException(_detail(response.body, 'Sign in failed (${response.statusCode}).'));
    }
    final sessionCookie = response.cookies.where((cookie) => cookie.name == _sessionCookieName).firstOrNull;
    if (sessionCookie == null) throw const HttpException('The server did not return a session cookie.');
    _cookie = '${sessionCookie.name}=${sessionCookie.value}';
    _csrf = response.headers.value(_csrfHeader);
    if (_csrf == null || _csrf!.isEmpty) throw const HttpException('The server did not return a CSRF token.');
    await _storage.write(key: 'session_cookie', value: _cookie);
    await _storage.write(key: 'csrf_token', value: _csrf);
  }

  Future<void> logout() async {
    try {
      await _request('DELETE', '/api/v1/session', csrf: true);
    } finally {
      await clearSession();
    }
  }

  Future<void> clearSession() async {
    _cookie = null;
    _csrf = null;
    await _storage.delete(key: 'session_cookie');
    await _storage.delete(key: 'csrf_token');
  }

  Future<List<Delivery>> inbox() async {
    final response = await _request('GET', '/api/v1/inbox', query: {'limit': '100'});
    if (response.statusCode != 200) throw HttpException('Inbox request failed (${response.statusCode}).');
    final decoded = jsonDecode(response.body) as List<dynamic>;
    return decoded.map((entry) => Delivery.fromJson(entry as Map<String, dynamic>)).toList();
  }

  Future<void> markRead(int deliveryId, bool read) async {
    final response = await _request(
      read ? 'POST' : 'DELETE',
      '/api/v1/inbox/$deliveryId/read',
      csrf: true,
    );
    if (response.statusCode != 200) throw HttpException('Read-state update failed (${response.statusCode}).');
  }

  Future<void> acknowledge(int deliveryId) async {
    final response = await _request('POST', '/api/v1/inbox/$deliveryId/acknowledge', csrf: true);
    if (response.statusCode != 200) throw HttpException('Acknowledgement failed (${response.statusCode}).');
  }

  Future<void> deleteDelivery(int deliveryId) async {
    final response = await _request('DELETE', '/api/v1/inbox/$deliveryId', csrf: true);
    if (response.statusCode != 204) {
      throw HttpException(_detail(response.body, 'Delete failed (${response.statusCode}).'));
    }
  }

  Future<void> createAndSubscribeChannel({
    required String slug,
    required String name,
    String? description,
  }) async {
    final create = await _request(
      'POST',
      '/api/v1/channels',
      csrf: true,
      jsonBody: {
        'slug': slug,
        'name': name,
        'description': description == null || description.trim().isEmpty ? null : description.trim(),
      },
    );
    if (create.statusCode != 201) {
      throw HttpException(_detail(create.body, 'Topic creation failed (${create.statusCode}).'));
    }
    final subscribe = await _request('PUT', '/api/v1/subscriptions/${Uri.encodeComponent(slug)}', csrf: true);
    if (subscribe.statusCode != 200) {
      throw HttpException(_detail(subscribe.body, 'Topic was created but subscription failed (${subscribe.statusCode}).'));
    }
  }

  Stream<Delivery> stream({int? afterId}) async* {
    while (_cookie != null) {
      try {
        final request = await _http.getUrl(_uri('/api/v1/inbox/stream', afterId == null ? null : {'after_id': '$afterId'}));
        request.headers.set(HttpHeaders.acceptHeader, 'text/event-stream');
        request.headers.set(HttpHeaders.cookieHeader, _cookie!);
        final response = await request.close();
        if (response.statusCode != 200) {
          await response.drain<void>();
          if (response.statusCode == 401) return;
          throw HttpException('Realtime stream failed (${response.statusCode}).');
        }

        var event = '';
        var eventId = '';
        final data = StringBuffer();
        await for (final line in response.transform(utf8.decoder).transform(const LineSplitter())) {
          if (line.isEmpty) {
            if (event == 'inbox' && data.isNotEmpty) {
              final delivery = Delivery.fromJson(jsonDecode(data.toString()) as Map<String, dynamic>);
              afterId = delivery.id;
              yield delivery;
            }
            event = '';
            eventId = '';
            data.clear();
            continue;
          }
          if (line.startsWith(':')) continue;
          if (line.startsWith('event:')) event = line.substring(6).trim();
          if (line.startsWith('id:')) eventId = line.substring(3).trim();
          if (line.startsWith('data:')) {
            if (data.isNotEmpty) data.write('\n');
            data.write(line.substring(5).trimLeft());
          }
        }
        if (eventId.isNotEmpty) afterId = int.tryParse(eventId) ?? afterId;
      } catch (_) {
        await Future<void>.delayed(const Duration(seconds: 3));
      }
    }
  }

  Future<_ApiResponse> _request(
    String method,
    String path, {
    Map<String, Object?>? jsonBody,
    Map<String, String>? query,
    bool authenticated = true,
    bool csrf = false,
  }) async {
    final request = await _http.openUrl(method, _uri(path, query));
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    if (authenticated && _cookie != null) request.headers.set(HttpHeaders.cookieHeader, _cookie!);
    if (csrf && _csrf != null) request.headers.set(_csrfHeader, _csrf!);
    if (jsonBody != null) {
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode(jsonBody));
    }
    final response = await request.close();
    final body = await utf8.decoder.bind(response).join();
    return _ApiResponse(response.statusCode, response.headers, response.cookies, body);
  }

  static String _detail(String body, String fallback) {
    try {
      final value = jsonDecode(body) as Map<String, dynamic>;
      return value['detail']?.toString() ?? fallback;
    } catch (_) {
      return fallback;
    }
  }
}

class _ApiResponse {
  _ApiResponse(this.statusCode, this.headers, this.cookies, this.body);
  final int statusCode;
  final HttpHeaders headers;
  final List<Cookie> cookies;
  final String body;
}

extension _FirstOrNull<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}

class ClientAlerts {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();

  Future<void> initialize() async {
    const settings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      linux: LinuxInitializationSettings(defaultActionName: 'Open GoreeCloud Notify'),
    );
    await _plugin.initialize(settings: settings);
  }

  Future<bool> requestPermission() async {
    if (!Platform.isAndroid) return true;
    return await _plugin
            .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
            ?.requestNotificationsPermission() ??
        false;
  }

  Future<void> show(Delivery delivery) => _plugin.show(
        id: delivery.id,
        title: 'GoreeCloud Notify',
        body: 'New notification received. Open Notify to view details.',
        payload: '${delivery.id}',
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails(
            'goreecloud_notify_messages',
            'GoreeCloud Notify messages',
            channelDescription: 'Private GoreeCloud notification alerts',
            importance: Importance.high,
            priority: Priority.high,
          ),
          linux: LinuxNotificationDetails(transient: true),
        ),
      );
}

class NotifyApp extends StatelessWidget {
  const NotifyApp({super.key, required this.api, required this.alerts});
  final NotifyApi api;
  final ClientAlerts alerts;

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'GoreeCloud Notify',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5A6CF0), brightness: Brightness.light),
        ),
        darkTheme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF8792FF), brightness: Brightness.dark),
        ),
        themeMode: ThemeMode.system,
        home: SessionGate(api: api, alerts: alerts),
      );
}

class SessionGate extends StatefulWidget {
  const SessionGate({super.key, required this.api, required this.alerts});
  final NotifyApi api;
  final ClientAlerts alerts;

  @override
  State<SessionGate> createState() => _SessionGateState();
}

class _SessionGateState extends State<SessionGate> {
  late Future<bool> _restore;
  @override
  void initState() {
    super.initState();
    _restore = widget.api.restoreSession();
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<bool>(
        future: _restore,
        builder: (context, snapshot) {
          if (!snapshot.hasData) return const Scaffold(body: Center(child: CircularProgressIndicator()));
          return snapshot.data!
              ? InboxScreen(api: widget.api, alerts: widget.alerts, onSignedOut: _signedOut)
              : LoginScreen(api: widget.api, onSignedIn: _signedIn);
        },
      );

  void _signedIn() => setState(() => _restore = Future.value(true));
  void _signedOut() => setState(() => _restore = Future.value(false));
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.api, required this.onSignedIn});
  final NotifyApi api;
  final VoidCallback onSignedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.notifications_active_rounded, size: 58),
                  const SizedBox(height: 16),
                  Text('GoreeCloud Notify', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 28),
                  TextField(controller: _username, autocorrect: false, decoration: const InputDecoration(labelText: 'Username', border: OutlineInputBorder())),
                  const SizedBox(height: 12),
                  TextField(controller: _password, obscureText: true, onSubmitted: (_) => _login(), decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder())),
                  if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
                  const SizedBox(height: 16),
                  FilledButton.icon(onPressed: _busy ? null : _login, icon: const Icon(Icons.login), label: Text(_busy ? 'Signing in…' : 'Sign in')),
                  const SizedBox(height: 12),
                  Text(widget.api.base.host, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
        ),
      );

  Future<void> _login() async {
    setState(() { _busy = true; _error = null; });
    try {
      await widget.api.login(_username.text.trim(), _password.text);
      widget.onSignedIn();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('HttpException: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class InboxScreen extends StatefulWidget {
  const InboxScreen({super.key, required this.api, required this.alerts, required this.onSignedOut});
  final NotifyApi api;
  final ClientAlerts alerts;
  final VoidCallback onSignedOut;

  @override
  State<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends State<InboxScreen> with WidgetsBindingObserver {
  final PersistentAlerts _persistentAlerts = PersistentAlerts();
  List<Delivery> _deliveries = const [];
  bool _loading = true;
  String? _error;
  StreamSubscription<Delivery>? _stream;
  AppLifecycleState _lifecycle = AppLifecycleState.resumed;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refresh().then((_) => _startStream());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) => _lifecycle = state;

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stream?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final items = await widget.api.inbox();
      if (mounted) setState(() { _deliveries = items; _loading = false; _error = null; });
    } catch (error) {
      if (mounted) setState(() { _loading = false; _error = error.toString(); });
    }
  }

  void _startStream() {
    _stream?.cancel();
    final latest = _deliveries.isEmpty ? null : _deliveries.map((item) => item.id).reduce((a, b) => a > b ? a : b);
    _stream = widget.api.stream(afterId: latest).listen((delivery) {
      if (!mounted) return;
      setState(() => _deliveries = [delivery, ..._deliveries.where((item) => item.id != delivery.id)]);
      if (_lifecycle != AppLifecycleState.resumed) widget.alerts.show(delivery);
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Notify'),
          actions: [
            IconButton(onPressed: _addTopic, tooltip: 'Add topic', icon: const Icon(Icons.add_circle_outline)),
            if (Platform.isAndroid)
              IconButton(
                onPressed: _enableSystemAlerts,
                tooltip: 'Enable system alerts',
                icon: const Icon(Icons.notifications_none),
              ),
            IconButton(onPressed: _refresh, tooltip: 'Refresh', icon: const Icon(Icons.refresh)),
            IconButton(onPressed: _logout, tooltip: 'Sign out', icon: const Icon(Icons.logout)),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center)))
                : RefreshIndicator(
                    onRefresh: _refresh,
                    child: _deliveries.isEmpty
                        ? ListView(children: const [SizedBox(height: 160), Center(child: Text('No notifications yet.'))])
                        : ListView.separated(
                            padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
                            itemCount: _deliveries.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (context, index) {
                              final delivery = _deliveries[index];
                              return _DeliveryCard(
                                delivery: delivery,
                                onRead: (read) async { await widget.api.markRead(delivery.id, read); await _refresh(); },
                                onAcknowledge: () async { await widget.api.acknowledge(delivery.id); await _refresh(); },
                                onDelete: () => _deleteDelivery(delivery),
                              );
                            },
                          ),
                  ),
      );

  Future<void> _addTopic() async {
    final name = TextEditingController();
    final slug = TextEditingController();
    final description = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add approved topic'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
              TextField(controller: slug, autocorrect: false, decoration: const InputDecoration(labelText: 'Topic slug', hintText: 'goreecloud-example')),
              TextField(controller: description, decoration: const InputDecoration(labelText: 'Description (optional)')),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Add topic')),
        ],
      ),
    );
    if (submitted != true || !mounted) return;
    final cleanName = name.text.trim();
    final cleanSlug = slug.text.trim().toLowerCase();
    if (cleanName.isEmpty || !RegExp(r'^[a-z0-9][a-z0-9._-]{0,119}$').hasMatch(cleanSlug)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a name and a valid lowercase topic slug.')));
      return;
    }
    try {
      await widget.api.createAndSubscribeChannel(
        slug: cleanSlug,
        name: cleanName,
        description: description.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Topic #$cleanSlug added and subscribed.')));
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString().replaceFirst('HttpException: ', ''))));
    }
  }

  Future<void> _deleteDelivery(Delivery delivery) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove from inbox?'),
        content: const Text('This removes only your inbox copy. It does not delete the underlying notification or another user\'s copy.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Remove')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.deleteDelivery(delivery.id);
      if (mounted) setState(() => _deliveries = _deliveries.where((item) => item.id != delivery.id).toList());
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString().replaceFirst('HttpException: ', ''))));
    }
  }

  Future<void> _enableSystemAlerts() async {
    final permissionGranted = await widget.alerts.requestPermission();
    if (!mounted) return;
    if (!permissionGranted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('System alerts were not enabled. You can continue using Notify in the app.'),
        ),
      );
      return;
    }

    final sessionCookie = widget.api.sessionCookie;
    if (sessionCookie == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('System alerts require an active signed-in session.')),
      );
      return;
    }

    final latest = _deliveries.isEmpty ? 0 : _deliveries.map((item) => item.id).reduce((a, b) => a > b ? a : b);
    final enabled = await _persistentAlerts.enable(
      server: widget.api.base,
      sessionCookie: sessionCookie,
      afterId: latest,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          enabled
              ? 'Persistent system alerts enabled. Notification content remains private.'
              : 'Persistent system alerts could not be enabled. You can continue using Notify in the app.',
        ),
      ),
    );
  }

  Future<void> _logout() async {
    await _stream?.cancel();
    if (Platform.isAndroid) await _persistentAlerts.disable();
    await widget.api.logout();
    widget.onSignedOut();
  }
}

class _DeliveryCard extends StatelessWidget {
  const _DeliveryCard({
    required this.delivery,
    required this.onRead,
    required this.onAcknowledge,
    required this.onDelete,
  });
  final Delivery delivery;
  final ValueChanged<bool> onRead;
  final VoidCallback onAcknowledge;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final read = delivery.readAt != null;
    final acknowledged = delivery.acknowledgedAt != null;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(delivery.title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: read ? FontWeight.w500 : FontWeight.w800))),
            _SeverityChip(delivery.severity),
          ]),
          const SizedBox(height: 8),
          Text(delivery.body),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 6, children: [
            Chip(label: Text(delivery.source)),
            Chip(label: Text(delivery.channel)),
            Chip(label: Text(_formatTime(delivery.createdAt))),
          ]),
          const SizedBox(height: 8),
          Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 6, children: [
            TextButton.icon(onPressed: onDelete, icon: const Icon(Icons.delete_outline), label: const Text('Remove')),
            TextButton.icon(onPressed: () => onRead(!read), icon: Icon(read ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined), label: Text(read ? 'Unread' : 'Read')),
            FilledButton.tonalIcon(onPressed: acknowledged ? null : onAcknowledge, icon: const Icon(Icons.done_all), label: Text(acknowledged ? 'Acknowledged' : 'Acknowledge')),
          ]),
        ]),
      ),
    );
  }

  static String _formatTime(DateTime value) => '${value.month}/${value.day} ${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
}

class _SeverityChip extends StatelessWidget {
  const _SeverityChip(this.value);
  final String value;
  @override
  Widget build(BuildContext context) => Chip(label: Text(value.toUpperCase()), visualDensity: VisualDensity.compact);
}
