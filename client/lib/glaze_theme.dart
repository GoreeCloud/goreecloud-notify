import 'dart:ui';

import 'package:flutter/material.dart';

/// GoreeCloud Notify native mapping for the Glaze UI 1.4 Stable semantics.
///
/// This intentionally maps shared Glaze roles into Flutter rather than copying
/// the web implementation. Solid/Raised surfaces remain the default content
/// materials; translucent Glaze surfaces are reserved for chrome and emphasis.
abstract final class GlazeTokens {
  static const double radiusSmall = 12;
  static const double radiusMedium = 16;
  static const double radiusControl = 18;
  static const double radiusLarge = 24;
  static const double radiusXLarge = 30;
  static const double radiusPill = 999;

  static const double targetMin = 44;
  static const double targetComfortable = 48;

  static const double space1 = 4;
  static const double space2 = 8;
  static const double space3 = 12;
  static const double space4 = 16;
  static const double space5 = 20;
  static const double space6 = 24;
  static const double space8 = 32;
  static const double space10 = 40;
  static const double space12 = 48;

  static const Color accent = Color(0xFF5D66B8);
  static const Color accentStrong = Color(0xFF4A54A2);
  static const Color info = Color(0xFF3F78C5);
  static const Color warning = Color(0xFFB87525);
  static const Color danger = Color(0xFFB65361);
  static const Color success = Color(0xFF3E8B6B);
}

ThemeData glazeTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = ColorScheme.fromSeed(
    seedColor: GlazeTokens.accent,
    brightness: brightness,
    surface: dark ? const Color(0xFF17181E) : const Color(0xFFF9F8FC),
  );

  final canvas = dark ? const Color(0xFF101116) : const Color(0xFFF4F2F8);
  final raised = dark ? const Color(0xFF202129) : const Color(0xFFFEFCFF);
  final outline = dark ? const Color(0xFF373942) : const Color(0xFFE0DDE8);

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme.copyWith(
      primary: dark ? const Color(0xFFAEB6FF) : GlazeTokens.accent,
      onPrimary: dark ? const Color(0xFF20285E) : Colors.white,
      surface: raised,
      outline: outline,
      outlineVariant: outline.withValues(alpha: .68),
    ),
    scaffoldBackgroundColor: canvas,
    canvasColor: canvas,
    dividerColor: outline.withValues(alpha: .72),
    textTheme: ThemeData(brightness: brightness).textTheme.copyWith(
      headlineLarge: TextStyle(
        fontSize: 38,
        height: 1.08,
        fontWeight: FontWeight.w700,
        letterSpacing: -1.2,
        color: dark ? const Color(0xFFF5F3FA) : const Color(0xFF202027),
      ),
      headlineMedium: TextStyle(
        fontSize: 30,
        height: 1.12,
        fontWeight: FontWeight.w700,
        letterSpacing: -.7,
        color: dark ? const Color(0xFFF5F3FA) : const Color(0xFF202027),
      ),
      titleLarge: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
      titleMedium: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      bodyLarge: const TextStyle(fontSize: 16, height: 1.5),
      bodyMedium: const TextStyle(fontSize: 14, height: 1.45),
      labelLarge: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: raised,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusLarge),
        side: BorderSide(color: outline.withValues(alpha: .74)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: dark ? const Color(0xFF1E2027) : const Color(0xFFFBF9FD),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(GlazeTokens.targetMin, GlazeTokens.targetComfortable),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(GlazeTokens.targetMin, GlazeTokens.targetMin),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      ),
    ),
    chipTheme: ChipThemeData(
      side: BorderSide(color: outline),
      backgroundColor: dark ? const Color(0xFF24262E) : const Color(0xFFF7F5FA),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
    ),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusMedium)),
    ),
    dialogTheme: DialogThemeData(
      elevation: 12,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge)),
    ),
  );
}

class GlazeChrome extends StatelessWidget {
  const GlazeChrome({super.key, required this.child, this.padding = EdgeInsets.zero});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final border = Theme.of(context).colorScheme.outlineVariant;
    return ClipRRect(
      borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: (dark ? const Color(0xFF252731) : Colors.white).withValues(alpha: dark ? .72 : .76),
            borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge),
            border: Border.all(color: border.withValues(alpha: .7)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: dark ? .24 : .08),
                blurRadius: 28,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}
