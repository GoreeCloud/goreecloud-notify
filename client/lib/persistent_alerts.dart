import 'dart:io';

import 'package:flutter/services.dart';

class PersistentAlerts {
  static const MethodChannel _channel = MethodChannel('com.goreecloud.notify/persistent_alerts');

  Future<bool> enable({
    required Uri server,
    required String sessionCookie,
    int afterId = 0,
  }) async {
    if (!Platform.isAndroid) return false;
    return await _channel.invokeMethod<bool>('enable', <String, Object>{
          'server': server.toString(),
          'cookie': sessionCookie,
          'afterId': afterId,
        }) ??
        false;
  }

  Future<bool> disable() async {
    if (!Platform.isAndroid) return false;
    return await _channel.invokeMethod<bool>('disable') ?? false;
  }

  Future<bool> isEnabled() async {
    if (!Platform.isAndroid) return false;
    return await _channel.invokeMethod<bool>('isEnabled') ?? false;
  }
}
