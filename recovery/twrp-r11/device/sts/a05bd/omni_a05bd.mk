#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit some common Omni stuff.
$(call inherit-product, vendor/omni/config/common.mk)

# Inherit from a05bd device
$(call inherit-product, device/sts/a05bd/device.mk)

PRODUCT_DEVICE := a05bd
PRODUCT_NAME := omni_a05bd
PRODUCT_BRAND := benesse
PRODUCT_MODEL := A05BD Ubuntu Touch recovery
PRODUCT_MANUFACTURER := sts

# Private candidate recovery identity; no stock release-key fingerprint claim.
