#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI module for ddQuint - macOS native application wrapper.

Provides a clean, native macOS interface for the ddQuint pipeline
with folder selection, progress tracking, interactive visualization,
and export capabilities.
"""

from .macos_native import ddQuintMacOSNativeApp, main

__all__ = ['ddQuintMacOSNativeApp', 'main']