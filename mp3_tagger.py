#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MP3 tag editor for Nemo and Nautilus."""
import os, sys, re, shutil, tempfile, gettext, traceback, subprocess, mimetypes
from pathlib import Path

