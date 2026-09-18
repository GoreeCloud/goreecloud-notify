import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_notify_client/glaze_theme.dart';

void main() {
  test('Glaze UI 1.5.1 identity and authority anchors are exact', () {
    expect(GlazeTokens.stableVersion, '1.5.1');
    expect(
      GlazeTokens.reviewedImplementationAnchor,
      'ee1032a0822ab8e103f8afe48e5c1859fde65cc9',
    );
    expect(
      GlazeTokens.sourceQualificationAnchor,
      '5b59d0e36950d737dba35b58ae58058684e0831b',
    );
  });

  testWidgets(
    'native presentation gives accessibility state precedence without authority escalation',
    (tester) async {
      late GlazeNativePresentationResolution resolution;

      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(520, 900),
              highContrast: true,
              disableAnimations: true,
              textScaler: TextScaler.linear(1.4),
            ),
            child: Builder(
              builder: (context) {
                resolution =
                    GlazeNativePresentationResolution.fromContext(context);
                return const SizedBox();
              },
            ),
          ),
        ),
      );

      expect(resolution.paneMode, GlazeNativePaneMode.single);
      expect(
        resolution.controlDensity,
        GlazeNativeControlDensity.comfortable,
      );
      expect(
        resolution.materialPreference,
        GlazeNativeMaterialPreference.solidAccessible,
      );
      expect(
        resolution.motionPreference,
        GlazeNativeMotionPreference.reduced,
      );
      expect(resolution.authorizationInferred, isFalse);
      expect(resolution.permissionGrantedByGlaze, isFalse);
      expect(resolution.automaticNavigationAllowed, isFalse);
      expect(resolution.automaticPermissionRequestAllowed, isFalse);
      expect(resolution.automaticConsequentialExecutionAllowed, isFalse);
      expect(resolution.telemetryRequired, isFalse);
      expect(resolution.remoteAnalysisRequired, isFalse);
    },
  );

  test('system-alert capability never grants permission or executes recovery', () {
    final unknown = GlazeCapabilityPresentation.systemAlerts(
      GlazeCapabilityState.unknown,
    );
    expect(unknown.state, GlazeCapabilityState.unknown);
    expect(unknown.userInitiatedRecovery, 'request-permission');
    expect(unknown.permissionGrantedByGlaze, isFalse);
    expect(unknown.automaticExecutionAllowed, isFalse);

    final restricted = GlazeCapabilityPresentation.systemAlerts(
      GlazeCapabilityState.restricted,
    );
    expect(restricted.state, GlazeCapabilityState.restricted);
    expect(restricted.userInitiatedRecovery, isNotNull);
    expect(restricted.permissionGrantedByGlaze, isFalse);
    expect(restricted.automaticExecutionAllowed, isFalse);
  });
}
