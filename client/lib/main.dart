import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'glaze_theme.dart';
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
    final response = await _request(read ? 'POST' : 'DELETE', '/api/v1/inbox/$deliveryId/read', csrf: true);
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
        theme: glazeTheme(Brightness.light),
        darkTheme: glazeTheme(Brightness.dark),
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
          if (!snapshot.hasData) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          return snapshot.data!
              ? InboxScreen(api: widget.api, alerts: widget.alerts, onSignedOut: _signedOut)
              : LoginScreen(api: widget.api, onSignedIn: _signedIn);
        },
      );

  void _signedIn() {
    setState(() {
      _restore = Future.value(true);
    });
  }

  void _signedOut() {
    setState(() {
      _restore = Future.value(false);
    });
  }
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: dark
                      ? const [Color(0xFF111219), Color(0xFF181927), Color(0xFF111218)]
                      : const [Color(0xFFF5F3FA), Color(0xFFEEEFFA), Color(0xFFF8F5F9)],
                ),
              ),
            ),
          ),
          Positioned(
            top: -140,
            right: -80,
            child: _GlowOrb(color: scheme.primary.withValues(alpha: dark ? .16 : .14), size: 420),
          ),
          Positioned(
            bottom: -180,
            left: -90,
            child: _GlowOrb(color: const Color(0xFFB693D1).withValues(alpha: dark ? .10 : .13), size: 440),
          ),
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(GlazeTokens.space6),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1040),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final desktop = constraints.maxWidth >= 760;
                    final intro = _AuthIntro(host: widget.api.base.host);
                    final form = GlazeChrome(
                      padding: const EdgeInsets.all(GlazeTokens.space8),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 420),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text('Welcome back', style: Theme.of(context).textTheme.headlineMedium),
                            const SizedBox(height: 8),
                            Text(
                              'Sign in to your private notification workspace.',
                              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: scheme.onSurfaceVariant),
                            ),
                            const SizedBox(height: 28),
                            TextField(
                              controller: _username,
                              autocorrect: false,
                              textInputAction: TextInputAction.next,
                              decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline_rounded)),
                            ),
                            const SizedBox(height: 14),
                            TextField(
                              controller: _password,
                              obscureText: true,
                              onSubmitted: (_) => _login(),
                              decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock_outline_rounded)),
                            ),
                            if (_error != null)
                              Padding(
                                padding: const EdgeInsets.only(top: 14),
                                child: _StatusBanner(message: _error!, danger: true),
                              ),
                            const SizedBox(height: 20),
                            FilledButton.icon(
                              onPressed: _busy ? null : _login,
                              icon: _busy
                                  ? const SizedBox.square(
                                      dimension: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.login_rounded),
                              label: Text(_busy ? 'Signing in…' : 'Sign in'),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.shield_outlined, size: 16, color: scheme.onSurfaceVariant),
                                const SizedBox(width: 7),
                                Flexible(
                                  child: Text(
                                    widget.api.base.host,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                    if (!desktop) {
                      return Column(children: [intro, const SizedBox(height: 24), form]);
                    }
                    return Row(
                      children: [
                        Expanded(flex: 5, child: intro),
                        const SizedBox(width: 42),
                        Expanded(flex: 4, child: form),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _error = null;
    });
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

class _AuthIntro extends StatelessWidget {
  const _AuthIntro({required this.host});
  final String host;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: scheme.primaryContainer,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Icon(Icons.notifications_active_rounded, size: 34, color: scheme.onPrimaryContainer),
          ),
          const SizedBox(height: 28),
          Text('GoreeCloud Notify', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 14),
          Text(
            'Private alerts, calm by default.',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(color: scheme.primary),
          ),
          const SizedBox(height: 18),
          Text(
            'A focused notification workspace for GoreeCloud services, designed with Glaze UI and privacy-preserving system alerts.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 28),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: const [
              _FeaturePill(icon: Icons.lock_outline_rounded, label: 'Private by default'),
              _FeaturePill(icon: Icons.bolt_outlined, label: 'Realtime delivery'),
              _FeaturePill(icon: Icons.devices_rounded, label: 'Cross-platform'),
            ],
          ),
        ],
      ),
    );
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
  int? _selectedId;

  Delivery? get _selected {
    for (final item in _deliveries) {
      if (item.id == _selectedId) return item;
    }
    return _deliveries.isEmpty ? null : _deliveries.first;
  }

  int get _unreadCount => _deliveries.where((item) => item.readAt == null).length;
  int get _criticalCount => _deliveries.where((item) => item.severity.toLowerCase() == 'critical').length;

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
      if (!mounted) return;
      setState(() {
        _deliveries = items;
        _selectedId = items.any((item) => item.id == _selectedId) ? _selectedId : (items.isEmpty ? null : items.first.id);
        _loading = false;
        _error = null;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = error.toString();
        });
      }
    }
  }

  void _startStream() {
    _stream?.cancel();
    final latest = _deliveries.isEmpty ? null : _deliveries.map((item) => item.id).reduce((a, b) => a > b ? a : b);
    _stream = widget.api.stream(afterId: latest).listen((delivery) {
      if (!mounted) return;
      setState(() {
        _deliveries = [delivery, ..._deliveries.where((item) => item.id != delivery.id)];
        _selectedId ??= delivery.id;
      });
      if (_lifecycle != AppLifecycleState.resumed) widget.alerts.show(delivery);
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final desktop = constraints.maxWidth >= 980;
            final wide = constraints.maxWidth >= 1380;
            final gutter = wide ? 28.0 : 18.0;
            return Padding(
              padding: EdgeInsets.all(gutter),
              child: desktop
                  ? Row(
                      children: [
                        SizedBox(width: wide ? 250 : 218, child: _Sidebar(apiHost: widget.api.base.host, unread: _unreadCount, onSignOut: _logout)),
                        SizedBox(width: gutter),
                        Expanded(child: _DesktopWorkspace(scheme: scheme)),
                      ],
                    )
                  : _CompactWorkspace(scheme: scheme),
            );
          },
        ),
      ),
    );
  }

  Widget _DesktopWorkspace({required ColorScheme scheme}) => Column(
        children: [
          _TopBar(
            title: 'Notifications',
            subtitle: '${_deliveries.length} total · $_unreadCount unread',
            onAddTopic: _addTopic,
            onEnableAlerts: Platform.isAndroid ? _enableSystemAlerts : null,
            onRefresh: _refresh,
          ),
          const SizedBox(height: 18),
          _SummaryStrip(total: _deliveries.length, unread: _unreadCount, critical: _criticalCount),
          const SizedBox(height: 18),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  flex: 9,
                  child: GlazeChrome(
                    padding: const EdgeInsets.all(10),
                    child: _buildList(compact: true),
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  flex: 11,
                  child: GlazeChrome(
                    padding: const EdgeInsets.all(24),
                    child: _selected == null
                        ? const _EmptyState()
                        : _DeliveryDetail(
                            delivery: _selected!,
                            onRead: (read) async {
                              await widget.api.markRead(_selected!.id, read);
                              await _refresh();
                            },
                            onAcknowledge: () async {
                              await widget.api.acknowledge(_selected!.id);
                              await _refresh();
                            },
                            onDelete: () => _deleteDelivery(_selected!),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ],
      );

  Widget _CompactWorkspace({required ColorScheme scheme}) => Column(
        children: [
          _TopBar(
            title: 'Notify',
            subtitle: '$_unreadCount unread',
            onAddTopic: _addTopic,
            onEnableAlerts: Platform.isAndroid ? _enableSystemAlerts : null,
            onRefresh: _refresh,
            onSignOut: _logout,
          ),
          const SizedBox(height: 14),
          Expanded(child: _buildList(compact: false)),
        ],
      );

  Widget _buildList({required bool compact}) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: _StatusBanner(message: _error!, danger: true));
    if (_deliveries.isEmpty) return const _EmptyState();
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.separated(
        padding: compact ? const EdgeInsets.all(4) : const EdgeInsets.only(bottom: 24),
        itemCount: _deliveries.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final delivery = _deliveries[index];
          return _DeliveryTile(
            delivery: delivery,
            selected: compact && delivery.id == _selected?.id,
            detailed: !compact,
            onTap: () {
              if (compact) {
                setState(() => _selectedId = delivery.id);
              }
            },
            onRead: (read) async {
              await widget.api.markRead(delivery.id, read);
              await _refresh();
            },
            onAcknowledge: () async {
              await widget.api.acknowledge(delivery.id);
              await _refresh();
            },
            onDelete: () => _deleteDelivery(delivery),
          );
        },
      ),
    );
  }

  Future<void> _addTopic() async {
    final name = TextEditingController();
    final slug = TextEditingController();
    final description = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add approved topic'),
        content: SizedBox(
          width: 430,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
              const SizedBox(height: 12),
              TextField(
                controller: slug,
                autocorrect: false,
                decoration: const InputDecoration(labelText: 'Topic slug', hintText: 'goreecloud-example'),
              ),
              const SizedBox(height: 12),
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
      await widget.api.createAndSubscribeChannel(slug: cleanSlug, name: cleanName, description: description.text);
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
      if (!mounted) return;
      setState(() {
        _deliveries = _deliveries.where((item) => item.id != delivery.id).toList();
        if (_selectedId == delivery.id) _selectedId = _deliveries.isEmpty ? null : _deliveries.first.id;
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString().replaceFirst('HttpException: ', ''))));
    }
  }

  Future<void> _enableSystemAlerts() async {
    final permissionGranted = await widget.alerts.requestPermission();
    if (!mounted) return;
    if (!permissionGranted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('System alerts were not enabled. You can continue using Notify in the app.')));
      return;
    }

    final sessionCookie = widget.api.sessionCookie;
    if (sessionCookie == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('System alerts require an active signed-in session.')));
      return;
    }

    final latest = _deliveries.isEmpty ? 0 : _deliveries.map((item) => item.id).reduce((a, b) => a > b ? a : b);
    final enabled = await _persistentAlerts.enable(server: widget.api.base, sessionCookie: sessionCookie, afterId: latest);
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

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.apiHost, required this.unread, required this.onSignOut});
  final String apiHost;
  final int unread;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return GlazeChrome(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(16)),
                child: Icon(Icons.notifications_active_rounded, color: scheme.onPrimaryContainer),
              ),
              const SizedBox(width: 12),
              const Expanded(child: Text('Notify', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 20))),
            ],
          ),
          const SizedBox(height: 28),
          _SidebarDestination(icon: Icons.inbox_rounded, label: 'Inbox', badge: '$unread', selected: true),
          const SizedBox(height: 8),
          const _SidebarDestination(icon: Icons.check_circle_outline_rounded, label: 'Acknowledged'),
          const SizedBox(height: 8),
          const _SidebarDestination(icon: Icons.settings_outlined, label: 'Preferences'),
          const Spacer(),
          Divider(color: scheme.outlineVariant),
          const SizedBox(height: 10),
          Row(
            children: [
              Icon(Icons.shield_outlined, size: 18, color: scheme.onSurfaceVariant),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  apiHost,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextButton.icon(onPressed: onSignOut, icon: const Icon(Icons.logout_rounded), label: const Text('Sign out')),
        ],
      ),
    );
  }
}

class _SidebarDestination extends StatelessWidget {
  const _SidebarDestination({required this.icon, required this.label, this.badge, this.selected = false});
  final IconData icon;
  final String label;
  final String? badge;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: selected ? scheme.primaryContainer.withValues(alpha: .72) : Colors.transparent,
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
      ),
      child: Row(
        children: [
          Icon(icon, size: 21, color: selected ? scheme.onPrimaryContainer : scheme.onSurfaceVariant),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label, style: TextStyle(fontWeight: selected ? FontWeight.w700 : FontWeight.w500)),
          ),
          if (badge != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: scheme.surface, borderRadius: BorderRadius.circular(999)),
              child: Text(badge!, style: Theme.of(context).textTheme.labelSmall),
            ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.title,
    required this.subtitle,
    required this.onAddTopic,
    required this.onRefresh,
    this.onEnableAlerts,
    this.onSignOut,
  });

  final String title;
  final String subtitle;
  final VoidCallback onAddTopic;
  final VoidCallback onRefresh;
  final VoidCallback? onEnableAlerts;
  final VoidCallback? onSignOut;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 3),
                Text(subtitle, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
              ],
            ),
          ),
          _CircleAction(icon: Icons.add_rounded, tooltip: 'Add topic', onPressed: onAddTopic),
          const SizedBox(width: 8),
          if (onEnableAlerts != null) ...[
            _CircleAction(icon: Icons.notifications_none_rounded, tooltip: 'Enable system alerts', onPressed: onEnableAlerts!),
            const SizedBox(width: 8),
          ],
          _CircleAction(icon: Icons.refresh_rounded, tooltip: 'Refresh', onPressed: onRefresh),
          if (onSignOut != null) ...[
            const SizedBox(width: 8),
            _CircleAction(icon: Icons.logout_rounded, tooltip: 'Sign out', onPressed: onSignOut!),
          ],
        ],
      );
}

class _CircleAction extends StatelessWidget {
  const _CircleAction({required this.icon, required this.tooltip, required this.onPressed});
  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: tooltip,
        child: Material(
          color: Theme.of(context).colorScheme.surface,
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: onPressed,
            child: SizedBox.square(dimension: 46, child: Icon(icon, size: 21)),
          ),
        ),
      );
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({required this.total, required this.unread, required this.critical});
  final int total;
  final int unread;
  final int critical;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(child: _MetricCard(label: 'All notifications', value: '$total', icon: Icons.notifications_none_rounded)),
          const SizedBox(width: 12),
          Expanded(child: _MetricCard(label: 'Unread', value: '$unread', icon: Icons.mark_email_unread_outlined)),
          const SizedBox(width: 12),
          Expanded(child: _MetricCard(label: 'Critical', value: '$critical', icon: Icons.priority_high_rounded, danger: critical > 0)),
        ],
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value, required this.icon, this.danger = false});
  final String label;
  final String value;
  final IconData icon;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final accent = danger ? GlazeTokens.danger : scheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(GlazeTokens.radiusLarge),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(color: accent.withValues(alpha: .12), borderRadius: BorderRadius.circular(14)),
            child: Icon(icon, color: accent, size: 21),
          ),
          const SizedBox(width: 14),
          Expanded(child: Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant))),
          Text(value, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _DeliveryTile extends StatelessWidget {
  const _DeliveryTile({
    required this.delivery,
    required this.selected,
    required this.detailed,
    required this.onTap,
    required this.onRead,
    required this.onAcknowledge,
    required this.onDelete,
  });

  final Delivery delivery;
  final bool selected;
  final bool detailed;
  final VoidCallback onTap;
  final ValueChanged<bool> onRead;
  final VoidCallback onAcknowledge;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final read = delivery.readAt != null;
    final acknowledged = delivery.acknowledgedAt != null;
    return Material(
      color: selected ? scheme.primaryContainer.withValues(alpha: .42) : scheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusLarge),
        side: BorderSide(color: selected ? scheme.primary.withValues(alpha: .42) : scheme.outlineVariant),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(GlazeTokens.radiusLarge),
        child: Padding(
          padding: EdgeInsets.all(detailed ? 18 : 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      delivery.title,
                      maxLines: detailed ? 2 : 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: read ? FontWeight.w600 : FontWeight.w800),
                    ),
                  ),
                  const SizedBox(width: 12),
                  _SeverityChip(delivery.severity),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                delivery.body,
                maxLines: detailed ? 3 : 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(read ? Icons.drafts_outlined : Icons.mark_email_unread_outlined, size: 16, color: scheme.primary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '${delivery.channel} · ${_formatTime(delivery.createdAt)}',
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                  ),
                  if (acknowledged) Icon(Icons.done_all_rounded, size: 17, color: GlazeTokens.success),
                ],
              ),
              if (detailed) ...[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    TextButton.icon(onPressed: onDelete, icon: const Icon(Icons.delete_outline_rounded), label: const Text('Remove')),
                    TextButton.icon(
                      onPressed: () => onRead(!read),
                      icon: Icon(read ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined),
                      label: Text(read ? 'Unread' : 'Read'),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: acknowledged ? null : onAcknowledge,
                      icon: const Icon(Icons.done_all_rounded),
                      label: Text(acknowledged ? 'Acknowledged' : 'Acknowledge'),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _DeliveryDetail extends StatelessWidget {
  const _DeliveryDetail({required this.delivery, required this.onRead, required this.onAcknowledge, required this.onDelete});
  final Delivery delivery;
  final ValueChanged<bool> onRead;
  final VoidCallback onAcknowledge;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final read = delivery.readAt != null;
    final acknowledged = delivery.acknowledgedAt != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _SeverityChip(delivery.severity),
            const Spacer(),
            Text(_formatTime(delivery.createdAt), style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
          ],
        ),
        const SizedBox(height: 24),
        Text(delivery.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 14),
        Text(delivery.body, style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: 26),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            _MetaPill(icon: Icons.source_outlined, text: delivery.source),
            _MetaPill(icon: Icons.tag_rounded, text: delivery.channel),
            _MetaPill(icon: read ? Icons.drafts_outlined : Icons.mark_email_unread_outlined, text: read ? 'Read' : 'Unread'),
            _MetaPill(icon: Icons.done_all_rounded, text: acknowledged ? 'Acknowledged' : 'Not acknowledged'),
          ],
        ),
        const Spacer(),
        Divider(color: scheme.outlineVariant),
        const SizedBox(height: 14),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          alignment: WrapAlignment.end,
          children: [
            TextButton.icon(onPressed: onDelete, icon: const Icon(Icons.delete_outline_rounded), label: const Text('Remove')),
            TextButton.icon(
              onPressed: () => onRead(!read),
              icon: Icon(read ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined),
              label: Text(read ? 'Mark unread' : 'Mark read'),
            ),
            FilledButton.icon(
              onPressed: acknowledged ? null : onAcknowledge,
              icon: const Icon(Icons.done_all_rounded),
              label: Text(acknowledged ? 'Acknowledged' : 'Acknowledge'),
            ),
          ],
        ),
      ],
    );
  }
}

class _SeverityChip extends StatelessWidget {
  const _SeverityChip(this.value);
  final String value;

  Color _color() {
    switch (value.toLowerCase()) {
      case 'critical':
        return GlazeTokens.danger;
      case 'warning':
        return GlazeTokens.warning;
      case 'info':
        return GlazeTokens.info;
      default:
        return GlazeTokens.accent;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .11),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: .32)),
      ),
      child: Text(value.toUpperCase(), style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: .4)),
    );
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: .56),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16),
            const SizedBox(width: 7),
            Text(text, style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600)),
          ],
        ),
      );
}

class _FeaturePill extends StatelessWidget {
  const _FeaturePill({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface.withValues(alpha: .72),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [Icon(icon, size: 17), const SizedBox(width: 7), Text(label)],
        ),
      );
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.message, this.danger = false});
  final String message;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final color = danger ? GlazeTokens.danger : GlazeTokens.info;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .10),
        borderRadius: BorderRadius.circular(GlazeTokens.radiusMedium),
        border: Border.all(color: color.withValues(alpha: .28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(danger ? Icons.error_outline_rounded : Icons.info_outline_rounded, color: color, size: 20),
          const SizedBox(width: 10),
          Flexible(child: Text(message, style: TextStyle(color: color, fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(22)),
              child: Icon(Icons.notifications_none_rounded, color: scheme.onPrimaryContainer, size: 30),
            ),
            const SizedBox(height: 18),
            Text('Nothing here yet', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 7),
            Text('New GoreeCloud notifications will appear here.', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant)),
          ],
        ),
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.color, required this.size});
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        ),
      );
}

String _formatTime(DateTime value) {
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.month}/${value.day} $hour:$minute';
}
