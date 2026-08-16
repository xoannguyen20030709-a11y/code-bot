import io
import json
import math
import time
import secrets
import string
import random
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

def create_hard_captcha():
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    width, height = 360, 120
    img = Image.new('RGB', (width, height), color=(12, 14, 22))
    draw = ImageDraw.Draw(img)

    for _ in range(35):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(secrets.randbelow(110) + 30, secrets.randbelow(110) + 30, secrets.randbelow(110) + 30), width=random.randint(1, 3))

    for _ in range(12):
        x0 = random.randint(-20, width - 20)
        y0 = random.randint(-20, height - 20)
        x1 = x0 + random.randint(40, 120)
        y1 = y0 + random.randint(40, 120)
        draw.arc([x0, y0, x1, y1], random.randint(0, 180), random.randint(180, 360), fill=(secrets.randbelow(120) + 40, secrets.randbelow(120) + 40, secrets.randbelow(120) + 40), width=2)

    resample_mode = getattr(Image, 'Resampling', Image).BICUBIC

    try:
        font = ImageFont.load_default(size=36)
    except TypeError:
        font = ImageFont.load_default()

    for i, char in enumerate(code):
        char_img = Image.new('RGBA', (45, 55), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((8, 2), char, fill=(secrets.randbelow(155) + 100, secrets.randbelow(155) + 100, secrets.randbelow(155) + 100), font=font)
        rotated = char_img.rotate(random.randint(-35, 35), expand=True, resample=resample_mode)
        img.paste(rotated, (18 + i * 54, random.randint(18, 30)), rotated)

    for _ in range(750):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(secrets.randbelow(190) + 60, secrets.randbelow(190) + 60, secrets.randbelow(190) + 60))

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer, code

def generate_keys(count: int, length: int):
    alphabet = string.ascii_uppercase + string.digits
    return [''.join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]

def calculate_entropy(length: int):
    return math.log2(36 ** length)

class ResultActionView(discord.ui.View):
    def __init__(self, keys: list, batch_id: str):
        super().__init__(timeout=300)
        self.keys = keys
        self.batch_id = batch_id

    @discord.ui.button(label='Tải File TXT', style=discord.ButtonStyle.secondary, emoji='📥')
    async def download_txt(self, interaction: discord.Interaction, button: discord.ui.Button):
        content = f"====================================\n  BATCH ID: {self.batch_id}\n  TOTAL KEYS: {len(self.keys)}\n====================================\n\n" + "\n".join(self.keys)
        file = discord.File(fp=io.BytesIO(content.encode('utf-8')), filename=f"Keys_{self.batch_id}.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @discord.ui.button(label='Tải File JSON', style=discord.ButtonStyle.secondary, emoji='🌐')
    async def download_json(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = {"batch_id": self.batch_id, "count": len(self.keys), "keys": self.keys}
        file = discord.File(fp=io.BytesIO(json.dumps(data, indent=4).encode('utf-8')), filename=f"Keys_{self.batch_id}.json")
        await interaction.response.send_message(file=file, ephemeral=True)

class CaptchaModal(discord.ui.Modal, title='🛡️ XÁC MINH CAPTCHA BẢO MẬT'):
    captcha_input = discord.ui.TextInput(
        label='Nhập Mã CAPTCHA (6 Ký Tự)',
        placeholder='Nhập chính xác các ký tự trong hình...',
        min_length=6,
        max_length=6,
        required=True
    )

    def __init__(self, correct_code: str, count: int, length: int):
        super().__init__()
        self.correct_code = correct_code
        self.count = count
        self.length = length

    async def on_submit(self, interaction: discord.Interaction):
        if self.captcha_input.value.strip().upper() != self.correct_code:
            embed_fail = discord.Embed(
                title="❌ XÁC MINH THẤT BẠI",
                description="```diff\n- Mã CAPTCHA không khớp với hình ảnh.\n- Vui lòng thực hiện lại lệnh /genkey.\n```",
                color=0xFF3838
            )
            return await interaction.response.send_message(embed=embed_fail, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        start = time.perf_counter()
        keys = generate_keys(self.count, self.length)
        elapsed = (time.perf_counter() - start) * 1000
        batch_id = f"BATCH-{secrets.token_hex(4).upper()}"
        entropy = calculate_entropy(self.length)

        embed = discord.Embed(
            title="⚡ TẠO DỮ LIỆU KEY THÀNH CÔNG ⚡",
            color=0x2B2D31
        )
        embed.add_field(
            name="📊 THÔNG SỐ HỆ THỐNG",
            value=f"```m\n• Mã Lô Key    : {batch_id}\n• Độ Dài Key   : {self.length} Ký Tự\n• Độ An Toàn   : {entropy:.1f} Bits Entropy\n• Tốc Độ Xử Lý : {elapsed:.2f} ms\n• Tổng Số Lượng: {self.count} Key```",
            inline=False
        )

        if self.count <= 15:
            formatted_keys = "\n".join([f"`{k}`" for k in keys])
            embed.add_field(
                name="🔑 DANH SÁCH KEY (CHẠM TRỰC TIẾP ĐỂ COPY)",
                value=formatted_keys,
                inline=False
            )
            embed.set_footer(text="📱 Tối ưu hóa chạm 1 lần để chép trên Mobile & PC", icon_url=interaction.user.display_avatar.url)
            view = ResultActionView(keys, batch_id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            content = "\n".join(keys).encode('utf-8')
            file = discord.File(fp=io.BytesIO(content), filename=f"Keys_{batch_id}.txt")
            embed.add_field(
                name="📂 XUẤT FILE TỰ ĐỘNG",
                value="```yaml\nSố lượng key > 15. Toàn bộ key đã được đóng gói vào file đính kèm bên dưới.```",
                inline=False
            )
            embed.set_footer(text="📱 Nhấn vào file bên dưới để tải toàn bộ danh sách", icon_url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)

class CaptchaView(discord.ui.View):
    def __init__(self, correct_code: str, count: int, length: int):
        super().__init__(timeout=90)
        self.correct_code = correct_code
        self.count = count
        self.length = length

    @discord.ui.button(label='Xác Minh & Tạo Key', style=discord.ButtonStyle.primary, emoji='🔓')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CaptchaModal(self.correct_code, self.count, self.length))

class KeyGenBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()

bot = KeyGenBot()

@bot.tree.command(name="genkey", description="Khởi tạo Key ngẫu nhiên hoa/số với CAPTCHA bảo mật dành cho Mobile & PC")
@app_commands.describe(count="Số lượng key cần tạo (1 - 2000)", length="Độ dài ký tự của key (4 - 128)")
async def genkey(interaction: discord.Interaction, count: int = 1, length: int = 8):
    if count < 1 or count > 2000:
        embed = discord.Embed(title="🚫 LỖI CẤU HÌNH", description="```fix\nSố lượng key phải từ 1 đến 2000.\n```", color=0xFF3838)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if length < 4 or length > 128:
        embed = discord.Embed(title="🚫 LỖI CẤU HÌNH", description="```fix\nĐộ dài key phải từ 4 đến 128 ký tự.\n```", color=0xFF3838)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    captcha_buffer, captcha_code = create_hard_captcha()
    captcha_file = discord.File(fp=captcha_buffer, filename="captcha.png")

    embed = discord.Embed(
        title="🛡️ HỆ THỐNG XÁC THỰC BẢO VỆ",
        description="```ini\n[ Yêu cầu xác nhận mã CAPTCHA chống Bot ]\n```\n> Nhấn nút **Xác Minh & Tạo Key** bên dưới và nhập đúng 6 ký tự trong hình.",
        color=0x5865F2
    )
    embed.set_image(url="attachment://captcha.png")
    embed.set_footer(text="Mã CAPTCHA hết hạn sau 90 giây")

    view = CaptchaView(captcha_code, count, length)
    await interaction.followup.send(embed=embed, file=captcha_file, view=view, ephemeral=True)

bot.run('MTUxMjcwODM4NTEzNTM5ODk1Mg.Gd6CWJ.w_jWikDBcXOs_QifBb7h-6fHrxA5Egrir_YCsM')
