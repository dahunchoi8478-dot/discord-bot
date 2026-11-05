import os
import re
import discord
from discord import app_commands
from discord.ext import commands

# 봇 권한 설정
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

TARGET_EMOJI = "🔫"

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

@bot.tree.command(name="명단", description="이모지가 반응된 가장 최근 메시지의 명단을 DM으로 받습니다.")
@app_commands.describe(키워드="특정 단어나 ID (비워두면 이모지가 달린 가장 최근 메시지 자동 선택)")
async def send_list(interaction: discord.Interaction, 키워드: str = None):
    await interaction.response.defer(ephemeral=True)

    channel = interaction.channel
    target_message = None

    if 키워드:
        # 1. 키워드가 ID(숫자)인 경우
        if 키워드.isdigit():
            try:
                target_message = await channel.fetch_message(int(키워드))
            except Exception:
                pass
        
        # 2. 키워드가 텍스트인 경우 최근 50개 메시지 중 검색
        if not target_message:
            search_word = 키워드.strip()
            async for msg in channel.history(limit=50):
                if search_word in msg.content:
                    target_message = msg
                    break
    else:
        # 3. 키워드가 없으면: 최근 메시지 30개 중 🎯이모지(🔫)가 달린 '가장 최근' 메시지 탐색
        async for msg in channel.history(limit=30):
            if msg.id == interaction.id:
                continue
            
            # 메시지에 지정된 이모지(🔫) 반응이 존재하는지 확인
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

    # 첫 줄 텍스트를 제목으로 표시
    first_line = target_message.content.splitlines()[0] if target_message.content else "이모지 반응 메시지"
    result_text = f"📋 **[{first_line}] 반응 명단 (총 {len(names)}명)**\n\n" + "\n".join(names)

    try:
        await interaction.user.send(result_text)
        await interaction.followup.send(f"**[{first_line}]** 명단을 DM으로 전송했습니다!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("DM을 보낼 수 없습니다. 디스코드 설정에서 '서버 멤버가 보내는 개인 메시지 허용'을 켜주세요.", ephemeral=True)

# Render 환경 변수에서 토큰을 안전하게 불러와 실행
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)