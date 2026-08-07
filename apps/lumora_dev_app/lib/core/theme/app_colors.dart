import 'package:flutter/material.dart';

class AppColors {
  AppColors._();
  static const deepPurple = Color(0xFF1A0A2E);
  static const purple = Color(0xFF7C3AED);
  static const violet = Color(0xFFA78BFA);
  static const electricBlue = Color(0xFF3B82F6);
  static const cyan = Color(0xFF22D3EE);
  static const black = Color(0xFF0A0A0F);
  static const surfaceDark = Color(0xFF12121A);
  static const cardDark = Color(0xFF1C1C28);
  static const elevatedDark = Color(0xFF252536);
  static const borderDark = Color(0xFF2E2E42);
  static const textPrimaryDark = Color(0xFFF5F3FF);
  static const textSecondaryDark = Color(0xFFA1A1B5);
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFEF4444);
  static const brandGradient = LinearGradient(
    colors: [purple, electricBlue],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
