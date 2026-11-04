#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),a05bd)
include $(call all-subdir-makefiles,$(LOCAL_PATH))
endif

ifeq ($(TARGET_DEVICE),a05bd)
include $(CLEAR_VARS)
LOCAL_MODULE := a05bd_recovery_watchdog
LOCAL_SRC_FILES := watchdog.c
LOCAL_FORCE_STATIC_EXECUTABLE := true
LOCAL_MODULE_PATH := $(TARGET_RECOVERY_ROOT_OUT)/sbin
LOCAL_MODULE_TAGS := optional
include $(BUILD_EXECUTABLE)
endif
