import os
import re
import discord
from discord import app_commands
from discord.ext import commands

# 📌 렌더 무료 플랜 절전 방지를 위한 웹서버 코드
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = threading.Thread(target=run)
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

# 📌 14단계 티어표 순서 정의
TIER_ORDER = [
    # 1단계
    "KillCam", "자몽", "짱가", "다후링", "잔돈", "Superdry",
    # 2단계
    "정호", "쌈닭", "공백", "으담", "스퍼맨",
    # 3단계
    "머저리", "curiousgirl", "쨍주", "은율", "함군", "킁킁", "아크틱", "기룽", "양채영", "야정한남자", "거북목치료사", "춘화",
    # 4단계
    "메뉴", "천사레인", "함장", "급할수록돌아가라", "눈모양",
    # 5단계
    "쩌렁", "불맨", "입원", "니니",
    # 6단계
    "말랑", "추성훈", "별전드", "리시드", "이새벽", "쉐용", "해바라기", "슈타", "동익", "한마디", "쬬앙", "보노보노", "죠스탕",
    # 7단계
    "드록바", "teket", "샷굔", "검지", "자켓2", "MIMO", "박민찬"
    # 8단계
    "로즈베리", "치우", "커뮤", "뽄뽄", "빅토리", "콩지히", "타마먀", "찬늘",
    # 9단계
    "복어", "다람쥐", "가리", "초모", "리운", "희생양", "지명", "파워플랜", "문태민",
    # 10단계
    "깜찍한무빙", "부리", "미미키티",
    # 11단계
    "탠구", "악동뽀로로", "난타", "Ellena", "강소이", "미니", "벤데타", "Ori", "귀욤", "안나",
    # 12단계
    "오리볶음탕", "꿀빵댕", "꼬꼬몽", "흰색말랑카우", "앙금", "퓻",
    # 13단계
    "삘링빨랑뿡", "서득만",
    # 14단계
    "허창건", "z워닝", "하보리", "꿍치"
]

@bot.event
async def on_ready():
    print(f"로그인 성공: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"명령어 동기화 완료: {len(synced)}개")
    except Exception as e:
        print(e)

def clean_nickname(name: str) -> str:
    """닉네임에서 2~4자리 년생 숫자 및 괄호/특수문자 제거"""
    name = re.sub(r'[\(\[\{]\s*\d{2,4}\s*[\)\]\}]', '', name)
    name = re.sub(r'^\s*\d{2,4}[\s_\-]*', '', name)
    name = re.sub(r'[\s_\-]*\d{2,4}\s*$', '', name)
    return name.strip()

@bot.tree.command(name="명단", description="이모지가 반응된 가장 최근 메시지의 명단을 티어표 순서대로 정렬하여 DM으로 받습니다.")
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
                str(reaction.emoji) == TARGET_EMOJI or 
                (hasattr(reaction.emoji, 'name') and reaction.emoji.name == "water_gun")
                for reaction in msg.reactions
            )
            
            if has_target_emoji:
                target_message = msg
                break

    if not target_message:
        await interaction.followup.send(f"{TARGET_EMOJI} 이모지가 달린 최근 메시지를 찾지 못했습니다.", ephemeral=True)
        return

    # 반응자 닉네임 수집
    names = []
    for reaction in target_message.reactions:
        if str(reaction.emoji) == TARGET_EMOJI or (hasattr(reaction.emoji, 'name') and reaction.emoji.name == "water_gun"):
            async for user in reaction.users():
                if user.bot:
                    continue
                
                member = interaction.guild.get_member(user.id)
                raw_name = member.display_name if member else user.name
                
                cleaned_name = clean_nickname(raw_name)
                if cleaned_name:
                    names.append(cleaned_name)

    if not names:
        await interaction.followup.send(f"찾은 메시지에서 {TARGET_EMOJI} 이모지를 누른 사용자가 없습니다.", ephemeral=True)
        return

    # 📌 티어표 순서(TIER_ORDER)에 따라 수집된 유저 정렬 (티어표에 없는 닉네임은 맨 뒤로)
    sorted_names = sorted(
        names, 
        key=lambda x: TIER_ORDER.index(x) if x in TIER_ORDER else 999
    )

    # 📌 [수정] 닉네임을 가로로 6명씩 묶어서 배치 (기호 없이 띄어쓰기만 적용)
    chunked_names = []
    for i in range(0, len(sorted_names), 6):
        chunk = sorted_names[i:i+6]
        chunked_names.append("  ".join(chunk))

    # 첫 줄 텍스트를 제목으로 표시
    first_line = target_message.content.splitlines()[0] if target_message.content else "이모지 반응 메시지"
    result_text = f"📋 **[{first_line}] 반응 명단 (총 {len(sorted_names)}명)**\n\n" + "\n".join(chunked_names)

    try:
        await interaction.user.send(result_text)
        await interaction.followup.send(f"**[{first_line}]** 티어 순서 정렬 명단을 DM으로 전송했습니다!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("DM을 보낼 수 없습니다. 디스코드 설정에서 '서버 멤버가 보내는 개인 메시지 허용'을 켜주세요.", ephemeral=True)

# Render 환경 변수에서 토큰을 안전하게 불러와 실행
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)