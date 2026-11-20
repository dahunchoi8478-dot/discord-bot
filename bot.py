import os
import re
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 📌 렌더 무료 플랜 절전 방지를 위한 웹서버 코드
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()

# 봇 실행 전에 웹서버 켜기
keep_alive()

# 봇 권한 설정
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

TARGET_EMOJI = "🔫"

# 📌 실시간 누른 순서 저장소 { message_id: [{'user_id': int, 'name': str}, ...] }
click_order_records = {}

# 📌 14단계 티어표 순서 정의 (기존 명단 그대로 유지)
TIER_ORDER = [
    # 1단계
    "자몽", "짱가", "다후링", "잔돈", "Superdry",
    # 2단계
    "정호", "쌈닭", "공백", "으담", "스퍼맨",
    # 3단계
    "머저리", "curiousgirl", "쨍주", "은율", "함군", "킁킁", "아크틱", "기룽", "양채영", "야정한남자", "거북목치료사", "춘화",
    # 4단계
    "메뉴", "천사레인", "함장", "급할수록돌아가라", "Vexx", "sitdown",
    # 5단계
    "쩌렁", "불맨", "입원", "니니", "눈모양",
    # 6단계
    "말랑", "추성훈", "별전드", "리시드", "쉐용", "해바라기", "슈타", "동익", "한마디", "쬬앙", "보노보노", "죠스탕",
    # 7단계
    "드록바", "teket", "샷굔", "검지", "자켓2", "MIMO",
    # 8단계
    "로즈베리", "치우", "커뮤", "뽄뽄", "빅토리", "콩지히", "타마먀", "찬늘", "엘로", "박민찬", "김연수",
    # 9단계
    "복어", "다람쥐", "가리", "초모", "리운", "희생양", "지명", "파워플랜", "문태민", "에이징.커브",
    # 10단계
    "깜찍한무빙", "부리", "미미키티",
    # 11단계
    "탠구", "악동뽀로로", "난타", "Ellena", "강소이", "미니", "벤데타", "Ori", "귀욤", "안나", "voldemort",
    # 12단계
    "오리볶음탕", "꿀빵댕", "꼬꼬몽", "흰색말랑카우", "앙금", "퓻",
    # 13단계
    "삘링빨랑뿡", "서득만",
    # 14단계
    "허창건", "하보리", "뾰다"
]


def is_target_emoji(emoji) -> bool:
    """🔫 (water_gun) 이모지 일치 여부 확인"""
    return str(emoji) == TARGET_EMOJI or (hasattr(emoji, "name") and emoji.name == "water_gun")


def clean_nickname(name: str) -> str:
    """닉네임에서 2~4자리 년생 숫자 및 괄호/특수문자 제거"""
    name = re.sub(r'[\(\[\{]\s*\d{2,4}\s*[\)\]\}]', '', name)
    name = re.sub(r'^\s*\d{2,4}[\s_\-]*', '', name)
    name = re.sub(r'[\s_\-]*\d{2,4}\s*$', '', name)
    return name.strip()


def format_chunked_lines(items: list[str], per_line: int = 6) -> list[str]:
    """문자열 리스트를 가로로 per_line명씩 묶어 반환"""
    lines = []
    for i in range(0, len(items), per_line):
        lines.append("  ".join(items[i:i + per_line]))
    return lines


async def resolve_display_name(guild: discord.Guild | None, user_id: int, payload_member: discord.Member | None = None, fallback_user: discord.abc.User | None = None) -> str:
    """서버 닉네임을 우선으로 가져오고 정제"""
    member = payload_member or (guild.get_member(user_id) if guild else None)
    if member is None and guild is not None:
        try:
            member = await guild.fetch_member(user_id)
        except Exception:
            member = None

    if member:
        raw_name = member.display_name
    elif fallback_user:
        raw_name = getattr(fallback_user, "display_name", None) or fallback_user.name
    else:
        raw_name = str(user_id)

    cleaned_name = clean_nickname(raw_name)
    return cleaned_name if cleaned_name else raw_name


@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"명령어 동기화 완료: {len(synced)}개")
    except Exception as e:
        print(e)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """이모지를 누를 때 순서 기록 (취소 후 재클릭 시 맨 뒤로 이동)"""
    if bot.user and payload.user_id == bot.user.id:
        return
    if not is_target_emoji(payload.emoji):
        return
    if payload.member and payload.member.bot:
        return

    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
    final_name = await resolve_display_name(guild, payload.user_id, payload_member=payload.member)
    if not final_name:
        return

    msg_id = payload.message_id
    if msg_id