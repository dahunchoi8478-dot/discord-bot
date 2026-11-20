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
    if msg_id not in click_order_records:
        click_order_records[msg_id] = []

    # 기존 기록 제거 후 맨 뒤에 추가 (재클릭 시 꼴찌 순서 반영)
    click_order_records[msg_id] = [
        r for r in click_order_records[msg_id] if r["user_id"] != payload.user_id
    ]
    click_order_records[msg_id].append({
        "user_id": payload.user_id,
        "name": final_name
    })


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """이모지 취소 시 누른 순서 기록에서 제거"""
    if not is_target_emoji(payload.emoji):
        return

    msg_id = payload.message_id
    if msg_id in click_order_records:
        click_order_records[msg_id] = [
            r for r in click_order_records[msg_id] if r["user_id"] != payload.user_id
        ]


@bot.tree.command(name="명단", description="이모지가 반응된 가장 최근 메시지의 명단을 티어표 순서와 누른 순서로 DM 전송합니다.")
@app_commands.describe(키워드="특정 단어나 ID (비워두면 이모지가 달린 가장 최근 메시지 자동 선택)")
async def send_list(interaction: discord.Interaction, 키워드: str = None):
    await interaction.response.defer(ephemeral=True)

    channel = interaction.channel
    target_message = None

    if 키워드:
        if 키워드.isdigit():
            try:
                target_message = await channel.fetch_message(int(키워드))
            except Exception:
                pass

        if not target_message:
            search_word = 키워드.strip()
            async for msg in channel.history(limit=50):
                if search_word in msg.content:
                    target_message = msg
                    break
    else:
        async for msg in channel.history(limit=30):
            if msg.id == interaction.id:
                continue

            has_target_emoji = any(
                is_target_emoji(reaction.emoji)
                for reaction in msg.reactions
            )

            if has_target_emoji:
                target_message = msg
                break

    if not target_message:
        await interaction.followup.send(f"{TARGET_EMOJI} 이모지가 달린 최근 메시지를 찾지 못했습니다.", ephemeral=True)
        return

    # 현재 메시지 기준 실제 반응자 수집
    active_users = []
    seen_ids = set()
    for reaction in target_message.reactions:
        if is_target_emoji(reaction.emoji):
            async for user in reaction.users():
                if user.bot or user.id in seen_ids:
                    continue
                seen_ids.add(user.id)

                final_name = await resolve_display_name(interaction.guild, user.id, fallback_user=user)
                if final_name:
                    active_users.append({
                        "user_id": user.id,
                        "name": final_name
                    })

    if not active_users:
        await interaction.followup.send(f"찾은 메시지에서 {TARGET_EMOJI} 이모지를 누른 사용자가 없습니다.", ephemeral=True)
        return

    active_id_map = {u["user_id"]: u["name"] for u in active_users}
    active_ids = set(active_id_map.keys())

    # 1) 티어표 순서 정렬
    tier_names = [u["name"] for u in active_users]
    sorted_tier_names = sorted(
        tier_names,
        key=lambda x: TIER_ORDER.index(x) if x in TIER_ORDER else 999
    )
    tier_lines = format_chunked_lines(sorted_tier_names, per_line=6)

    # 2) 누른 순서 동기화 (취소자 제외 + 봇 켜지기 전 기존 반응자 보완)
    recorded = [
        {"user_id": r["user_id"], "name": active_id_map[r["user_id"]]}
        for r in click_order_records.get(target_message.id, [])
        if r["user_id"] in active_ids
    ]
    recorded_ids = {r["user_id"] for r in recorded}

    for u in active_users:
        if u["user_id"] not in recorded_ids:
            recorded.append(u)

    click_order_records[target_message.id] = recorded

    # 전체 기준 1번부터 끊기지 않게 번호 부여 후 6명씩 한 줄로 묶기
    numbered_click_items = [
        f"{idx}. {r['name']}"
        for idx, r in enumerate(recorded, start=1)
    ]
    click_lines = format_chunked_lines(numbered_click_items, per_line=6)

    # 첫 줄 텍스트를 제목으로 표시
    first_line = target_message.content.splitlines()[0] if target_message.content else "이모지 반응 메시지"
    result_text = (
        f"📋 **[{first_line}] 반응 명단 (총 {len(active_users)}명)**\n\n"
        f"**📊 티어표 순서**\n" + "\n".join(tier_lines) + "\n\n"
        f"**⏱️ 누른 순서**\n" + "\n".join(click_lines)
    )

    try:
        await interaction.user.send(result_text)
        await interaction.followup.send(f"**[{first_line}]** 티어 순서 및 누른 순서 명단을 DM으로 전송했습니다!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("DM을 보낼 수 없습니다. 디스코드 설정에서 '서버 멤버가 보내는 개인 메시지 허용'을 켜주세요.", ephemeral=True)


# Render 환경 변수에서 토큰을 안전하게 불러와 실행
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)