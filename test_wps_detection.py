#!/usr/bin/env python3
"""
测试 WPS 表单 URL 检测
"""

def detect_form_type(url: str) -> str:
    """检测表单类型"""
    if 'docs.qq.com/form' in url:
        return 'tencent_docs'
    elif 'mikecrm.com' in url:
        return 'mikecrm'
    elif 'wjx.cn' in url:
        return 'wjx'
    elif 'jsj.top' in url or 'jinshuju.net' in url:
        return 'jinshuju'
    elif 'shimo.im' in url:
        return 'shimo'
    elif 'baominggongju.com' in url or 'p.baominggongju.com' in url:
        return 'baominggongju'
    elif 'credamo.com' in url:
        return 'credamo'
    elif 'wenjuan.com' in url:
        return 'wenjuan'
    elif 'fanqier.cn' in url:
        return 'fanqier'
    elif 'feishu.cn' in url:
        return 'feishu'
    elif 'kdocs.cn' in url or 'wps.cn' in url or 'wps.com' in url:
        return 'kdocs'
    elif 'wj.qq.com' in url:
        return 'tencent_wj'
    else:
        return 'unknown'


def test_wps_urls():
    """测试 WPS 表单 URL 检测"""
    test_cases = [
        # WPS 表单 URL
        ('https://f.wps.cn/g/Mk366xJl/', 'kdocs', 'WPS 短链接'),
        ('https://kdocs.cn/l/xxxxx', 'kdocs', 'kdocs 域名'),
        ('https://www.wps.cn/form/xxxxx', 'kdocs', 'wps.cn 域名'),
        ('https://www.wps.com/form/xxxxx', 'kdocs', 'wps.com 域名'),
        
        # 其他表单 URL（确保不受影响）
        ('https://docs.qq.com/form/page/xxxxx', 'tencent_docs', '腾讯文档'),
        ('https://www.mikecrm.com/xxxxx', 'mikecrm', '麦客CRM'),
        ('https://www.wjx.cn/xxxxx', 'wjx', '问卷星'),
        ('https://shimo.im/forms/xxxxx', 'shimo', '石墨文档'),
        ('https://jinshuju.net/f/xxxxx', 'jinshuju', '金数据'),
        
        # 未知类型
        ('https://example.com/form', 'unknown', '未知表单'),
    ]
    
    print("🧪 测试 WPS 表单 URL 检测\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for url, expected, description in test_cases:
        result = detect_form_type(url)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {description}")
        print(f"   URL: {url}")
        print(f"   期望: {expected}, 实际: {result}")
        print()
    
    print("=" * 80)
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查代码。")
    
    return failed == 0


if __name__ == '__main__':
    success = test_wps_urls()
    exit(0 if success else 1)

