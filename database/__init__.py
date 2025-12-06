"""
数据库模块 - MongoDB 版本
"""
from .models import Card, CardConfigItem, Link, FillRecord, User, Device, Category, Notice, NoticeCategory, Platform, CardEditRequest, Notification, FieldLibrary, FixedTemplate, init_database
from .db_manager import DatabaseManager

__all__ = ['Card', 'CardConfigItem', 'Link', 'FillRecord', 'User', 'Device', 'Category', 'Notice', 'NoticeCategory', 'Platform', 'CardEditRequest', 'Notification', 'FieldLibrary', 'FixedTemplate', 'DatabaseManager', 'init_database']
