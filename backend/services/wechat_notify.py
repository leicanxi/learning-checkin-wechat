"""
微信订阅消息服务
- access_token 缓存与刷新
- 发送订阅消息
"""
import time
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

# access_token 内存缓存
_token_cache = {
    "access_token": "",
    "expires_at": 0,  # unix timestamp
}


async def get_access_token() -> str:
    """获取微信 access_token，自动缓存和刷新"""
    now = time.time()
    # 提前 5 分钟刷新，避免临界过期
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["access_token"]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_APPSECRET,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        data = resp.json()

    if "errcode" in data and data["errcode"] != 0:
        logger.error(f"获取 access_token 失败: {data}")
        raise Exception(f"微信 access_token 获取失败: {data.get('errmsg', '')}")

    access_token = data["access_token"]
    expires_in = data.get("expires_in", 7200)

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in

    logger.info(f"access_token 已刷新，有效期 {expires_in} 秒")
    return access_token


async def send_subscribe_message(
    openid: str,
    template_id: str,
    data: dict,
    page: str = "",
    miniprogram_state: str = "trial",
) -> bool:
    """
    发送订阅消息

    :param openid: 接收者 openid
    :param template_id: 模板 ID
    :param data: 模板数据，格式如 {"thing1": {"value": "xx"}, "time2": {"value": "xx"}}
    :param page: 点击消息跳转的小程序页面路径（可选）
    :param miniprogram_state: 小程序版本类型 - formal(正式版), trial(体验版), developer(开发版)
    :return: 是否发送成功
    """
    access_token = await get_access_token()

    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"

    body = {
        "touser": openid,
        "template_id": template_id,
        "page": page,
        "data": data,
        "miniprogram_state": miniprogram_state,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, timeout=10)
        result = resp.json()

    if result.get("errcode") == 0:
        logger.info(f"订阅消息发送成功: openid={openid[:8]}...")
        return True
    else:
        logger.error(f"订阅消息发送失败: {result}")
        return False


async def send_daily_checkin_reminder(openid: str, reminder_time: str) -> bool:
    """
    发送每日打卡提醒

    :param openid: 用户 openid
    :param reminder_time: 提醒时间，如 "21:00"
    """
    template_id = settings.WECHAT_TMPL_DAILY_CHECKIN
    if not template_id:
        logger.warning("未配置每日打卡提醒模板 ID，跳过发送")
        return False

    return await send_subscribe_message(
        openid=openid,
        template_id=template_id,
        data={
            "thing1": {"value": "学习打卡时间到啦"},
            "time2": {"value": reminder_time},
            "thing3": {"value": "今天的学习任务还在等你，快来打卡吧！"},
        },
        page="pages/home/home",
    )


async def send_task_deadline_notify(openid: str, task_name: str, deadline: str) -> bool:
    """
    发送任务到期通知

    :param openid: 用户 openid
    :param task_name: 任务名称
    :param deadline: 截止时间
    """
    template_id = settings.WECHAT_TMPL_TASK_DEADLINE
    if not template_id:
        logger.warning("未配置任务到期通知模板 ID，跳过发送")
        return False

    return await send_subscribe_message(
        openid=openid,
        template_id=template_id,
        data={
            "thing1": {"value": task_name[:20]},
            "time2": {"value": deadline},
            "thing3": {"value": "你的学习任务即将到期，记得按时完成哦！"},
        },
        page="pages/planner/planner",
    )
