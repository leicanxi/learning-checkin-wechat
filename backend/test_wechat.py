"""测试微信 API 配置是否正确"""
import httpx
import asyncio
from config import settings

async def main():
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_APPSECRET,
        "js_code": "test",
        "grant_type": "authorization_code",
    }
    print(f"Testing with appid={settings.WECHAT_APPID}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    print(f"Response: {data}")
    # errcode 40029 = invalid code (expected since we used 'test')
    # errcode 40125 = invalid appsecret
    if data.get("errcode") == 40125:
        print("ERROR: appsecret 不正确！")

asyncio.run(main())
