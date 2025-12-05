# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import json
import altair as alt
import streamlit.components.v1 as components
import calendar
import random
import time
from datetime import date, datetime, timedelta
from openai import OpenAI

# 尝试导入 plotly
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ==========================================
# 1. 全局配置 & 核心数据
# ==========================================
FILE_NAME = 'daily_review_data.csv'
st.set_page_config(page_title="个人成长游戏系统", layout="wide", page_icon="🎮")

# === CSS 样式 ===
st.markdown("""
    <style>
        /* 强制优先使用 Emoji 字体 */
        html, body, [class*="css"], button, div {
            font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Segoe UI", sans-serif !important;
        }
        
        .badge-worn {
            border: 2px solid #FFD700;
            border-radius: 10px;
            padding: 2px 8px;
            background-color: rgba(255, 215, 0, 0.1);
            font-weight: bold;
            color: #d4ac0d;
            font-size: 0.8em;
        }
        
        .big-emoji {
            font-size: 60px;
            text-align: center;
            margin-bottom: 10px;
            display: block;
        }
        
        /* 属性卡片容器 (Grid布局) - 强制同一行 */
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 5px;
            margin-bottom: 15px;
            width: 100%;
        }
        
        /* 手机端适配：屏幕变窄时自动调整为3列 */
        @media (max-width: 600px) {
            .stat-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        /* 单个属性卡片 */
        .stat-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 8px 2px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-width: 0; /* 防止内容撑破 */
        }
        .stat-title { font-size: 12px; color: #6c757d; margin-bottom: 2px; white-space: nowrap; }
        .stat-value { font-size: 16px; font-weight: bold; color: #2c3e50; margin: 0; }
        .stat-delta { font-size: 10px; color: #27ae60; font-weight: bold; }
        .stat-avg   { font-size: 9px; color: #95a5a6; margin-top: 2px; white-space: nowrap; }
        
        /* 战利品框 */
        .reward-box {
            border: 2px dashed #f1c40f;
            padding: 15px;
            border-radius: 10px;
            background-color: rgba(241, 196, 15, 0.1);
            text-align: center;
            margin: 10px 0;
        }
        .reward-val { font-size: 24px; font-weight: bold; color: #d35400; }
        
        .tag-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
            padding: 5px;
        }
        .soul-tag {
            display: inline-block;
            padding: 4px 12px;
            margin: 2px;
            border-radius: 16px;
            background-color: #e8f0fe;
            color: #1a73e8;
            border: 1px solid #d2e3fc;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* Boss 战 */
        .boss-container-demon {
            border: 2px solid #8e44ad; border-radius: 10px; padding: 20px;
            background-color: rgba(142, 68, 173, 0.05); margin-bottom: 20px;
        }
        .boss-title-demon { color: #8e44ad; font-size: 24px; font-weight: bold; }
        
        .boss-container-truth {
            border: 2px solid #2980b9; border-radius: 10px; padding: 20px;
            background-color: rgba(41, 128, 185, 0.05); margin-bottom: 20px;
        }
        .boss-title-truth { color: #2980b9; font-size: 24px; font-weight: bold; }
        
        /* 塔罗牌文本 */
        .tarot-roman { font-family: 'Times New Roman', serif; font-size: 12px; color: #888; text-align: center; }
        .tarot-en { font-family: 'Georgia', serif; font-size: 14px; font-weight: bold; text-align: center; margin-bottom: 0px; }
        .tarot-cn { font-size: 16px; text-align: center; color: #555; margin-bottom: 5px; font-weight: bold; }
        .tarot-meta { font-size: 11px; text-align: center; color: #999; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- JS 注入 ---
def inject_custom_js():
    js_code = """
    <script>
        function updateAutocomplete() {
            const textareas = window.parent.document.querySelectorAll('textarea');
            textareas.forEach(el => { el.setAttribute('autocomplete', 'off'); });
            const inputs = window.parent.document.querySelectorAll('input[type="text"]');
            inputs.forEach(el => { el.setAttribute('autocomplete', 'off'); });
        }
        updateAutocomplete();
        const observer = new MutationObserver(updateAutocomplete);
        observer.observe(window.parent.document.body, { childList: true, subtree: true });
    </script>
    """
    components.html(js_code, height=0)

inject_custom_js()

# --- 数据列名定义 ---
COLS_META    = ['具体时间', '地点', '天气', '温度']
COLS_READING = ['阅读数据_JSON', '已读列表_JSON'] 
COLS_MORNING = ['晨_学习', '晨_锻炼', '晨_娱乐', '晨_冥想', '晨_反思']
COLS_DAY     = ['昼_收获', '昼_感受', '昼_失误']
COLS_NIGHT   = ['晚_学习', '晚_锻炼', '晚_娱乐', '晚_冥想', '晚_反思']
COLS_CHECKS  = ['晨_锻炼_Check', '晨_娱乐_Check', '晨_冥想_Check', 
                '晚_锻炼_Check', '晚_娱乐_Check', '晚_冥想_Check']
COLS_ENERGY  = ['初始_感受', '初始_点赞', '结算_感受', '结算_点赞']
COLS_BASE    = ['日期', '初始状态', '结算状态', '每日总结', '佩戴成就_JSON', '印象标签_JSON', '深渊凝视_JSON']
COLS_STATS   = ['属性_智慧', '属性_体质', '属性_心力', '属性_意志', '属性_魅力']
COLS_LOOT    = ['每日奇遇_JSON', '卡牌掉落_JSON']

ALL_COLUMNS = COLS_BASE + COLS_STATS + COLS_META + COLS_ENERGY + COLS_READING + \
              COLS_MORNING + COLS_DAY + COLS_NIGHT + COLS_CHECKS + COLS_LOOT

# --- 常量 ---
WEA_OPTS = ['晴', '多云', '阴', '小雨', '中雨', '大雨', '雪', '雾', '霾', '手动输入']
LABEL_MAP = {
    "学习": "学习/输入", "锻炼": "锻炼/活动", "娱乐": "娱乐/游戏", "冥想": "冥想/休息", "反思": "反思/梳理",
    "收获": "收获/做对", "感受": "感受/体验", "失误": "失误/问题",
    "Check": "(已打卡)"
}

# --- 塔罗牌数据 (78张) ---
MAJOR_ARCANA = [
    {"id": 0, "name": "愚者", "en": "The Fool", "roman": "0", "rarity": "SSR", "prob": "1%", "icon": "🃏", "desc": "无限的可能性，新的开始", "group": "大阿卡纳"},
    {"id": 1, "name": "魔术师", "en": "The Magician", "roman": "I", "rarity": "SR", "prob": "5%", "icon": "🪄", "desc": "创造力，掌握资源", "group": "大阿卡纳"},
    {"id": 2, "name": "女祭司", "en": "The High Priestess", "roman": "II", "rarity": "SR", "prob": "5%", "icon": "📜", "desc": "直觉，潜意识，智慧", "group": "大阿卡纳"},
    {"id": 3, "name": "女皇", "en": "The Empress", "roman": "III", "rarity": "SR", "prob": "5%", "icon": "👑", "desc": "丰饶，自然，母性", "group": "大阿卡纳"},
    {"id": 4, "name": "皇帝", "en": "The Emperor", "roman": "IV", "rarity": "SR", "prob": "5%", "icon": "🤴", "desc": "权威，结构，稳固", "group": "大阿卡纳"},
    {"id": 5, "name": "教皇", "en": "The Hierophant", "roman": "V", "rarity": "SR", "prob": "5%", "icon": "⛪", "desc": "传统，信仰，指导", "group": "大阿卡纳"},
    {"id": 6, "name": "恋人", "en": "The Lovers", "roman": "VI", "rarity": "SR", "prob": "5%", "icon": "💑", "desc": "爱，和谐，选择", "group": "大阿卡纳"},
    {"id": 7, "name": "战车", "en": "The Chariot", "roman": "VII", "rarity": "SR", "prob": "5%", "icon": "🐎", "desc": "意志力，胜利，控制", "group": "大阿卡纳"},
    {"id": 8, "name": "力量", "en": "Strength", "roman": "VIII", "rarity": "SR", "prob": "5%", "icon": "🦁", "desc": "勇气，耐心，内在力量", "group": "大阿卡纳"},
    {"id": 9, "name": "隐士", "en": "The Hermit", "roman": "IX", "rarity": "SR", "prob": "5%", "icon": "🕯️", "desc": "内省，孤独，寻求真理", "group": "大阿卡纳"},
    {"id": 10, "name": "命运之轮", "en": "Wheel of Fortune", "roman": "X", "rarity": "SSR", "prob": "1%", "icon": "🎡", "desc": "转折点，机遇，循环", "group": "大阿卡纳"},
    {"id": 11, "name": "正义", "en": "Justice", "roman": "XI", "rarity": "SR", "prob": "5%", "icon": "⚖️", "desc": "公平，真理，因果", "group": "大阿卡纳"},
    {"id": 12, "name": "倒吊人", "en": "The Hanged Man", "roman": "XII", "rarity": "SR", "prob": "5%", "icon": "🙃", "desc": "牺牲，新视角，等待", "group": "大阿卡纳"},
    {"id": 13, "name": "死神", "en": "Death", "roman": "XIII", "rarity": "SR", "prob": "5%", "icon": "💀", "desc": "结束，重生，转变", "group": "大阿卡纳"},
    {"id": 14, "name": "节制", "en": "Temperance", "roman": "XIV", "rarity": "SR", "prob": "5%", "icon": "🏺", "desc": "平衡，耐心，治愈", "group": "大阿卡纳"},
    {"id": 15, "name": "恶魔", "en": "The Devil", "roman": "XV", "rarity": "SR", "prob": "5%", "icon": "😈", "desc": "束缚，欲望，物质", "group": "大阿卡纳"},
    {"id": 16, "name": "高塔", "en": "The Tower", "roman": "XVI", "rarity": "SR", "prob": "5%", "icon": "⚡", "desc": "突变，觉醒，破坏", "group": "大阿卡纳"},
    {"id": 17, "name": "星星", "en": "The Star", "roman": "XVII", "rarity": "SR", "prob": "5%", "icon": "🌟", "desc": "希望，灵感，宁静", "group": "大阿卡纳"},
    {"id": 18, "name": "月亮", "en": "The Moon", "roman": "XVIII", "rarity": "SR", "prob": "5%", "icon": "🌙", "desc": "幻觉，恐惧，潜意识", "group": "大阿卡纳"},
    {"id": 19, "name": "太阳", "en": "The Sun", "roman": "XIX", "rarity": "SR", "prob": "5%", "icon": "☀️", "desc": "成功，快乐，活力", "group": "大阿卡纳"},
    {"id": 20, "name": "审判", "en": "Judgement", "roman": "XX", "rarity": "SR", "prob": "5%", "icon": "📯", "desc": "觉醒，召唤，重生", "group": "大阿卡纳"},
    {"id": 21, "name": "世界", "en": "The World", "roman": "XXI", "rarity": "SSR", "prob": "1%", "icon": "🌍", "desc": "圆满，达成，旅程终点", "group": "大阿卡纳"}
]

SUITS = [
    {"name": "权杖", "en": "Wands", "icon": "🪵", "desc": "行动、创造、激情", "group": "权杖"},
    {"name": "圣杯", "en": "Cups", "icon": "🏆", "desc": "情感、关系、直觉", "group": "圣杯"},
    {"name": "宝剑", "en": "Swords", "icon": "🗡️", "desc": "思维、理智、冲突", "group": "宝剑"},
    {"name": "星币", "en": "Pentacles", "icon": "🪙", "desc": "物质、金钱、工作", "group": "星币"}
]
RANKS = [
    {"r": "Ace", "n": "王牌", "rarity": "R", "prob": "20%"},
    {"r": "Two", "n": "二", "rarity": "N", "prob": "60%"},
    {"r": "Three", "n": "三", "rarity": "N", "prob": "60%"},
    {"r": "Four", "n": "四", "rarity": "N", "prob": "60%"},
    {"r": "Five", "n": "五", "rarity": "N", "prob": "60%"},
    {"r": "Six", "n": "六", "rarity": "N", "prob": "60%"},
    {"r": "Seven", "n": "七", "rarity": "N", "prob": "60%"},
    {"r": "Eight", "n": "八", "rarity": "N", "prob": "60%"},
    {"r": "Nine", "n": "九", "rarity": "N", "prob": "60%"},
    {"r": "Ten", "n": "十", "rarity": "N", "prob": "60%"},
    {"r": "Page", "n": "侍从", "rarity": "R", "prob": "20%"},
    {"r": "Knight", "n": "骑士", "rarity": "R", "prob": "20%"},
    {"r": "Queen", "n": "王后", "rarity": "R", "prob": "20%"},
    {"r": "King", "n": "国王", "rarity": "R", "prob": "20%"}
]

MINOR_ARCANA = []
card_id_counter = 22
for suit in SUITS:
    for rank in RANKS:
        card = {
            "id": card_id_counter,
            "name": f"{suit['name']}{rank['n']}",
            "en": f"{rank['r']} of {suit['en']}",
            "roman": "-", 
            "rarity": rank['rarity'],
            "prob": rank['prob'],
            "icon": suit['icon'],
            "desc": f"{suit['desc']} - {rank['r']} (小阿卡纳)",
            "group": suit['group']
        }
        MINOR_ARCANA.append(card)
        card_id_counter += 1

TAROT_DATA = MAJOR_ARCANA + MINOR_ARCANA

# --- 2. 十大成就数据 ---
ACHIEVEMENT_DATA = [
    {"id": "day_3", "name": "初出茅庐", "icon": "🥉", "desc": "累计复盘 3 天", "target": 3, "type": "days"},
    {"id": "day_10", "name": "习惯养成", "icon": "🥈", "desc": "累计复盘 10 天", "target": 10, "type": "days"},
    {"id": "day_50", "name": "长期主义", "icon": "🥇", "desc": "累计复盘 50 天", "target": 50, "type": "days"},
    {"id": "day_100", "name": "百日筑基", "icon": "🏆", "desc": "累计复盘 100 天", "target": 100, "type": "days"},
    {"id": "journey", "name": "生命之旅", "icon": "🌍", "desc": "集齐 22 张大阿卡纳", "type": "cards"},
    {"id": "element_lord", "name": "元素领主", "icon": "🔱", "desc": "集齐任意一套花色(14张)", "type": "cards"},
    {"id": "lucky_one", "name": "欧皇", "icon": "✨", "desc": "获得首张 SSR", "type": "cards"},
    {"id": "card_all", "name": "命运主宰", "icon": "🔮", "desc": "集齐 78 张塔罗牌", "target": 78, "type": "cards"},
    {"id": "hex_warrior", "name": "六边形战士", "icon": "🔯", "desc": "全属性累积 > 100", "type": "attr"},
    {"id": "early_bird", "name": "早睡才能早起", "icon": "💤", "desc": "连续21天22:00前复盘", "type": "habit"},
    {"id": "energetic", "name": "生龙活虎", "icon": "🐉", "desc": "累计锻炼打卡 100 次", "type": "habit"},
    {"id": "read_1", "name": "开卷有益", "icon": "📘", "desc": "完结 1 本书", "target": 1, "type": "read"},
    {"id": "read_3", "name": "知识求索者", "icon": "🧐", "desc": "完结 3 本书", "target": 3, "type": "read"},
    {"id": "read_10", "name": "博览群书", "icon": "🎓", "desc": "完结 10 本书", "target": 10, "type": "read"},
    {"id": "read_50", "name": "移动图书馆", "icon": "🏛️", "desc": "完结 50 本书", "target": 50, "type": "read"},
    {"id": "abyss_5", "name": "内省萌芽", "icon": "🕯️", "desc": "完成 5 次心灵试炼", "target": 5, "type": "abyss"},
    {"id": "abyss_20", "name": "心智觉醒", "icon": "💡", "desc": "完成 20 次心灵试炼", "target": 20, "type": "abyss"},
    {"id": "abyss_100", "name": "真理贤者", "icon": "🧙‍♂️", "desc": "完成 100 次心灵试炼", "target": 100, "type": "abyss"}
]

# --- Session State ---
if 'reading_list' not in st.session_state: st.session_state.reading_list = []
if 'last_selected_date' not in st.session_state: st.session_state.last_selected_date = None
if 'ai_response' not in st.session_state: st.session_state.ai_response = ""
if 'loot_revealed' not in st.session_state: st.session_state.loot_revealed = {}
if 'card_flipped' not in st.session_state: st.session_state.card_flipped = {}
if 'gallery_tab' not in st.session_state: st.session_state.gallery_tab = "大阿卡纳"
if 'boss_active' not in st.session_state: st.session_state.boss_active = False
if 'boss_data' not in st.session_state: st.session_state.boss_data = {}
if 'boss_card_revealed' not in st.session_state: st.session_state.boss_card_revealed = False

if 'view_year' not in st.session_state: st.session_state.view_year = date.today().year
if 'view_month' not in st.session_state: st.session_state.view_month = date.today().month
if 'wea_select' not in st.session_state: st.session_state['wea_select'] = '晴'

ai_config_pack = None

# --- 辅助函数 ---
def get_time_options():
    options = []
    for h in range(23, -1, -1):
        for m in range(55, -1, -5): options.append(f"{h:02d}:{m:02d}")
    return options
TIME_OPTIONS = get_time_options()

def get_nearest_time_index(target_time_obj):
    if not target_time_obj: return 0
    t_str = target_time_obj.strftime("%H:%M")
    target_m = int(t_str.split(':')[0])*60 + int(t_str.split(':')[1])
    best_idx, min_diff = 0, 9999
    for i, opt in enumerate(TIME_OPTIONS):
        opt_m = int(opt.split(':')[0])*60 + int(opt.split(':')[1])
        diff = abs(opt_m - target_m)
        if diff < min_diff: min_diff=diff; best_idx=i
    return best_idx

def load_data():
    """核心数据加载函数"""
    if not os.path.exists(FILE_NAME): return pd.DataFrame(columns=ALL_COLUMNS)
    try:
        df = pd.read_csv(FILE_NAME, dtype=str, encoding='utf-8-sig')
        if '每日成就' in df.columns and '每日总结' not in df.columns:
            df = df.rename(columns={'每日成就': '每日总结'})
        
        # 补全缺失列
        for col in ALL_COLUMNS:
            if col not in df.columns:
                if col.endswith('_Check'): df[col] = "False"
                elif col.startswith("属性_"): df[col] = "0"
                elif col == '卡牌掉落_JSON': df[col] = "[]"
                elif col == '佩戴成就_JSON': df[col] = "{}"
                elif col == '印象标签_JSON': df[col] = "[]"
                elif col == '深渊凝视_JSON': df[col] = "{}"
                else: df[col] = "" 
        
        # JSON 列处理
        json_dict_cols = ['佩戴成就_JSON', '深渊凝视_JSON', '每日奇遇_JSON']
        json_list_cols = ['卡牌掉落_JSON', '阅读数据_JSON', '已读列表_JSON', '印象标签_JSON']
        
        for c in json_dict_cols:
            if c in df.columns:
                df[c] = df[c].fillna("{}")
                df.loc[df[c] == "", c] = "{}"
        
        for c in json_list_cols:
            if c in df.columns:
                df[c] = df[c].fillna("[]")
                df.loc[df[c] == "", c] = "[]"

        df = df.fillna("")
        for col in COLS_STATS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['日期_dt'] = pd.to_datetime(df['日期'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=ALL_COLUMNS)

def get_book_history(df, book_name):
    history = []
    df_sorted = df.dropna(subset=['日期_dt']).sort_values('日期_dt')
    for _, row in df_sorted.iterrows():
        found = False; current_page=0; note=""
        try:
            for b in json.loads(row.get('阅读数据_JSON', '[]')):
                if b.get('name') == book_name:
                    current_page=int(b.get('current', 0)); note=b.get('note',''); found=True; break
        except: pass
        if not found:
            try:
                for b in json.loads(row.get('已读列表_JSON', '[]')):
                    if b.get('name') == book_name:
                        current_page=int(b.get('total', 0)); note=b.get('note',''); found=True; break
            except: pass
        if found: history.append({'日期':row['日期_dt'], '页数':current_page, '感悟':note})
    return pd.DataFrame(history)

def draw_tarot_cards(total_score):
    """抽卡逻辑"""
    draw_count = 1
    if total_score >= 10: draw_count += 1
    if total_score >= 15: draw_count += 1
    drawn = []
    for _ in range(draw_count):
        rand = random.random()
        if rand < 0.01: rarity = "SSR"
        elif rand < 0.10: rarity = "SR"
        elif rand < 0.40: rarity = "R"
        else: rarity = "N"
        pool = [c for c in TAROT_DATA if c['rarity'] == rarity]
        if not pool: pool = TAROT_DATA
        drawn.append(random.choice(pool))
    return drawn

def draw_boss_card(score):
    """深渊凝视专属抽卡"""
    if score < 60: return None, 0.0
    ssr_prob = 0.01; sr_prob = 0.10
    multiplier = 1.0
    if score >= 95: multiplier = 10.0
    elif score >= 80: multiplier = 5.0
    elif score >= 60: multiplier = 2.0
    current_ssr = min(1.0, ssr_prob * multiplier)
    current_sr = min(1.0, sr_prob * multiplier)
    rand = random.random()
    if rand < current_ssr: rarity = "SSR"
    elif rand < (current_ssr + current_sr): rarity = "SR"
    elif rand < 0.8: rarity = "R"
    else: rarity = "N"
    pool = [c for c in TAROT_DATA if c['rarity'] == rarity]
    if not pool: pool = TAROT_DATA
    return random.choice(pool), multiplier

# === AI 逻辑集合 ===
def get_ai_analysis_and_score(data_context, current_tags, api_key, base_url, model):
    if not api_key: return None, None, []
    tag_prompt = f"""
    【任务3：更新玩家印象标签】
    玩家目前的印象标签为：{current_tags}
    请根据今日日记更新标签：
    1. 忽略主观自夸，只看客观行为。
    2. **救赎机制**：如果现有标签中包含“xxx-改观中”，请重点检查今日是否有该负面行为。
       - 如果表现良好，请移除该标签。
       - 如果表现不好，去掉后缀，变回“xxx”。
    3. 发现新特点则添加。
    4. 保持 3-6 个简练标签。
    """
    prompt = f"""
    你是“灵魂之镜”。请根据玩家日记完成以下任务。
    【任务1：属性评分】
    对5个维度打分（0-5分）：智慧、体质、心力、意志、魅力。
    评分务必**极其严格**。普通记录仅给 0.5-1 分。只有突破性行为才能给 2-3 分。

    【任务2：生成每日奇遇 (严禁编造，必须基于真实知识)】
    1. **智慧符文**：匹配一个真实存在的思维模型或科学定律。
    2. **吟游诗篇**：引用一句人类历史上的经典文学/电影/名言。
    3. **异闻碎片**：提供一个与日记名词相关的客观冷知识。

    {tag_prompt}
    【玩家日记】
    {data_context}
    【输出格式】
    严格JSON: 
    {{
        "is_valid": true, 
        "scores": {{"智慧": 0, "体质": 0, "心力": 0, "意志": 0, "魅力": 0}},
        "loot": {{
            "rune": {{"title": "", "desc": ""}},
            "poem": {{"content": "", "source": ""}},
            "trivia": {{"content": ""}}
        }},
        "tags": ["标签1", "标签2"] 
    }}
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=0.1
        )
        raw = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        res_json = json.loads(raw)
        return res_json.get('scores'), res_json.get('loot'), res_json.get('tags', [])
    except Exception as e: return None, None, []

def generate_history_tags(df, ai_config):
    if not ai_config or not ai_config.get('key'): return False
    recent_df = df.sort_values('日期').tail(7)
    history_text = ""
    for _, r in recent_df.iterrows():
        history_text += f"[{r['日期']}] {r.get('每日总结','')}\n"
    prompt = f"""
    你是“灵魂之镜”。请根据玩家最近的历史复盘，建立印象标签。
    规则：只看客观行为，忽略自夸。提炼 3-6 个简练标签。
    【历史记录】
    {history_text}
    【输出格式】
    严格JSON: {{"tags": ["标签1", "标签2"]}}
    """
    try:
        client = OpenAI(api_key=ai_config['key'], base_url=ai_config['base'])
        response = client.chat.completions.create(
            model=ai_config['model'], messages=[{"role": "user", "content": prompt}], temperature=0.1
        )
        raw = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        tags = json.loads(raw).get('tags', [])
        if tags and not df.empty:
            idx = df.index[-1]
            df.at[idx, '印象标签_JSON'] = json.dumps(tags, ensure_ascii=False)
            df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            return tags
    except: return []
    return []

def generate_boss_encounter(df, ai_config, books_list):
    if not ai_config: return None
    recent_df = df.sort_values('日期').tail(7)
    txt = ""
    for _, r in recent_df.iterrows():
        txt += f"{r['日期']}: {r.get('每日总结','')}\n"
    try: latest_tags = json.loads(df.iloc[-1].get('印象标签_JSON', '[]'))
    except: latest_tags = []
    books_str = ", ".join([b['name'] for b in books_list if not b.get('finish_date')])
    prompt = f"""
    你是“灵魂之镜”的试炼官。请根据玩家状态生成一个挑战。
    【玩家数据】
    近期日记：{txt}
    当前标签：{latest_tags}
    在读书籍：{books_str}
    【决策逻辑】
    1. **心魔试炼 (demon)**：如果玩家有明显的负面标签，生成一个心魔 BOSS，进行严厉的质问。
    2. **真理探寻 (truth)**：如果玩家状态良好，生成一位智者，结合书籍内容或哲学问题进行苏格拉底式提问。
    【输出格式】
    严格JSON: 
    {{
        "type": "demon" 或 "truth",
        "name": "对象名", 
        "intro": "描述", 
        "question": "问题"
    }}
    """
    try:
        client = OpenAI(api_key=ai_config['key'], base_url=ai_config['base'])
        res = client.chat.completions.create(
            model=ai_config['model'], messages=[{"role": "user", "content": prompt}], temperature=0.7
        )
        return json.loads(res.choices[0].message.content.replace("```json","").replace("```","").strip())
    except: return None

def resolve_boss_battle(question, answer, ai_config, mode):
    if len(answer) < 15: return None 
    prompt = f"""
    玩家正在进行心灵试炼（模式：{mode}）。
    问题：{question}
    回答：{answer}
    请评价回答的深度和真诚度（0-100分）。
    【输出格式】
    严格JSON: 
    {{
        "score": 0, 
        "comment": "寄语", 
        "exp_distribution": {{"智慧": 0.5, "意志": 1.0}},
        "modify_tag": {{"old": "拖延", "new": "拖延-改观中"}} (可为null),
        "remove_tag": "...",
        "add_tag": "..."
    }}
    """
    try:
        client = OpenAI(api_key=ai_config['key'], base_url=ai_config['base'])
        res = client.chat.completions.create(
            model=ai_config['model'], messages=[{"role": "user", "content": prompt}], temperature=0.1
        )
        return json.loads(res.choices[0].message.content.replace("```json","").replace("```","").strip())
    except: return None

def check_early_bird(df):
    try:
        valid_streak = 0
        max_streak = 0
        df_sorted = df.sort_values('日期_dt')
        for _, row in df_sorted.iterrows():
            t_str = str(row.get('具体时间', '23:59'))
            if len(t_str) >= 5 and t_str < "22:00": valid_streak += 1
            else: valid_streak = 0
            max_streak = max(max_streak, valid_streak)
        return max_streak >= 21
    except: return False

def check_and_unlock_achievements(df):
    unlocked = []
    total_days = len(df)
    abyss_count = 0
    for _, r in df.iterrows():
        try:
            if json.loads(r.get('深渊凝视_JSON', '{}')).get('completed'): abyss_count += 1
        except: pass
    all_cards = []
    for _, r in df.iterrows():
        try: all_cards.extend(json.loads(r.get('卡牌掉落_JSON', '[]')))
        except: pass
    unique_cards = len(set(c['id'] for c in all_cards))
    
    # 核心修复：安全检查 target 字段
    for ach in ACHIEVEMENT_DATA:
        is_ok = False
        # 1. 天数成就
        if ach['type'] == 'days':
             if 'target' in ach and total_days >= ach['target']: is_ok = True
        # 2. 深渊成就
        elif ach['type'] == 'abyss':
             if 'target' in ach and abyss_count >= ach['target']: is_ok = True
        # 3. 属性成就
        elif ach['type'] == 'attr' and ach['id'] == 'hex_warrior':
            sums = [df[c].sum() for c in COLS_STATS]
            if all(s > 100 for s in sums): is_ok = True
        # 4. 卡牌成就 (逻辑分流)
        elif ach['type'] == 'cards':
            if ach['id'] == 'journey': # 22张大阿卡纳
                major_ids = set(range(22))
                if major_ids.issubset(set(c['id'] for c in all_cards)): is_ok = True
            elif ach['id'] == 'element_lord': # 任意花色
                if len(all_cards) >= 14: is_ok = True 
            elif ach['id'] == 'lucky_one': # SSR
                if 'SSR' in set(c['rarity'] for c in all_cards): is_ok = True
            elif ach['id'] == 'card_all': # 全收集
                if unique_cards >= 78: is_ok = True
        # 5. 习惯成就
        elif ach['type'] == 'habit':
            if ach['id'] == 'early_bird':
                if check_early_bird(df): is_ok = True
            elif ach['id'] == 'energetic':
                m_ex = df['晨_锻炼_Check'].apply(lambda x: str(x)=='True').sum()
                n_ex = df['晚_锻炼_Check'].apply(lambda x: str(x)=='True').sum()
                if (m_ex + n_ex) >= 100: is_ok = True
        # 6. 阅读成就
        elif ach['type'] == 'read':
            read_count = 0
            for _, r in df.iterrows():
                try: read_count += len(json.loads(r.get('已读列表_JSON', '[]')))
                except: pass
            if 'target' in ach and read_count >= ach['target']: is_ok = True
            
        if is_ok: unlocked.append(ach)
    return unlocked

def save_record(data_dict, ai_config=None):
    scores = {"智慧":0, "体质":0, "心力":0, "意志":0, "魅力":0}
    loot_data = {}
    card_drops = []
    content_len = 0
    for k, v in data_dict.items():
        if isinstance(v, str) and k not in ['日期', '具体时间']: content_len += len(v)
    if ai_config and ai_config.get('key'):
        if content_len < 5: st.toast("内容过少，未触发AI结算", icon=":material/block:")
        else:
            context = f"总结: {data_dict.get('每日总结','')}\n能量: {data_dict.get('初始状态')}->{data_dict.get('结算状态')}\n"
            for k, v in data_dict.items():
                if k.startswith(('晨_', '昼_', '晚_')) and not k.endswith('_Check') and v:
                    context += f"{k}: {v}\n"
            if data_dict.get('晨_锻炼_Check') == 'True': context += "晨间锻炼打卡\n"
            
            df_old = load_data()
            if not df_old.empty:
                 try: current_tags = json.loads(df_old.iloc[-1].get('印象标签_JSON', '[]'))
                 except: current_tags = []
            else: current_tags = []

            with st.spinner("🔮 灵魂之镜正在审视你..."):
                try:
                    ai_scores, ai_loot, new_tags = get_ai_analysis_and_score(context, current_tags, ai_config['key'], ai_config['base'], ai_config['model'])
                    if ai_scores:
                        if sum(ai_scores.values()) > 0:
                            scores.update(ai_scores)
                            st.toast(f"属性更新: {scores}", icon="🆙")
                            if ai_loot: loot_data = ai_loot
                            total_s = sum(scores.values())
                            card_drops = draw_tarot_cards(total_s)
                            data_dict['印象标签_JSON'] = json.dumps(new_tags, ensure_ascii=False)
                        else: st.toast("内容深度不足", icon="😶")
                    else: st.toast("AI 判定无效", icon="🚫")
                except: pass
    
    data_dict['属性_智慧'] = scores['智慧']
    data_dict['属性_体质'] = scores['体质']
    data_dict['属性_心力'] = scores['心力']
    data_dict['属性_意志'] = scores['意志']
    data_dict['属性_魅力'] = scores['魅力']
    
    if loot_data: data_dict['每日奇遇_JSON'] = json.dumps(loot_data, ensure_ascii=False)
    elif '每日奇遇_JSON' not in data_dict:
        df_old = load_data()
        mask = df_old['日期'] == str(data_dict['日期'])
        if mask.any(): data_dict['每日奇遇_JSON'] = df_old[mask].iloc[0].get('每日奇遇_JSON', '{}')

    if card_drops: data_dict['卡牌掉落_JSON'] = json.dumps(card_drops, ensure_ascii=False)
    elif '卡牌掉落_JSON' not in data_dict:
        df_old = load_data()
        mask = df_old['日期'] == str(data_dict['日期'])
        if mask.any(): data_dict['卡牌掉落_JSON'] = df_old[mask].iloc[0].get('卡牌掉落_JSON', '[]')

    if '佩戴成就_JSON' not in data_dict:
        df_old = load_data()
        mask = df_old['日期'] == str(data_dict['日期'])
        if mask.any(): data_dict['佩戴成就_JSON'] = df_old[mask].iloc[0].get('佩戴成就_JSON', '{}')
        elif not df_old.empty: data_dict['佩戴成就_JSON'] = df_old.iloc[-1].get('佩戴成就_JSON', '{}')

    if '印象标签_JSON' not in data_dict:
         df_old = load_data()
         mask = df_old['日期'] == str(data_dict['日期'])
         if mask.any(): data_dict['印象标签_JSON'] = df_old[mask].iloc[0].get('印象标签_JSON', '[]')
         elif not df_old.empty: data_dict['印象标签_JSON'] = df_old.iloc[-1].get('印象标签_JSON', '[]')
         else: data_dict['印象标签_JSON'] = '[]'
    
    if '深渊凝视_JSON' not in data_dict: data_dict['深渊凝视_JSON'] = '{}'

    df = load_data()
    if '日期_dt' in df.columns: del df['日期_dt']
    target_date = str(data_dict['日期'])
    if not df.empty: df = df[df['日期'] != target_date]
    new_row = pd.DataFrame([data_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    
    try:
        df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
        time.sleep(0.5)
        new_achievements = check_and_unlock_achievements(df)
        if new_achievements: st.toast(f"🎉 解锁成就：{len(new_achievements)} 个", icon="🏆")
        return True
    except: return False

def call_ai_coach(api_key, base_url, model_name, prompt):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        res = client.chat.completions.create(
            model=model_name, messages=[{"role":"user","content":prompt}], temperature=0.7
        )
        return res.choices[0].message.content
    except Exception as e: return f"错误: {e}"

def toggle_collection_callback(date_str, loot_type):
    try:
        df_curr = load_data()
        target_date_str = pd.to_datetime(date_str).strftime('%Y-%m-%d')
        mask_curr = df_curr['日期'] == target_date_str
        if mask_curr.any():
            idx = df_curr[mask_curr].index[0]
            loot = json.loads(df_curr.at[idx, '每日奇遇_JSON'])
            if loot_type not in loot: loot[loot_type] = {}
            loot[loot_type]['collected'] = not loot[loot_type].get('collected', False)
            df_curr.at[idx, '每日奇遇_JSON'] = json.dumps(loot, ensure_ascii=False)
            if '日期_dt' in df_curr.columns: del df_curr['日期_dt']
            df_curr.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            time.sleep(0.1)
    except: pass

def equip_badge_callback(badge_json_str):
    try:
        df = load_data()
        if not df.empty:
            df['日期_dt'] = pd.to_datetime(df['日期'], errors='coerce')
            df = df.sort_values('日期_dt')
            idx = df.index[-1]
            current_wear = df.at[idx, '佩戴成就_JSON']
            new_wear = "{}" if current_wear == badge_json_str else badge_json_str
            df.at[idx, '佩戴成就_JSON'] = new_wear
            if '日期_dt' in df.columns: del df['日期_dt']
            df.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
            st.toast("佩戴状态更新", icon="🛡️")
            time.sleep(0.5)
    except: pass

def reveal_card_callback(card_key):
    st.session_state.card_flipped[card_key] = True

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("玩家控制台")
    with st.expander("AI 配置", expanded=True):
        ai_provider = st.selectbox("服务商", ["Kimi (月之暗面)", "DeepSeek (深度求索)", "自定义"])
        if ai_provider == "Kimi (月之暗面)":
            default_base = "https://api.moonshot.cn/v1"
            default_model = "moonshot-v1-8k"
            key_help = "platform.moonshot.cn"
        elif ai_provider == "DeepSeek (深度求索)":
            default_base = "https://api.deepseek.com"
            default_model = "deepseek-chat"
            key_help = "platform.deepseek.com"
        else:
            default_base = ""
            default_model = ""
            key_help = "OpenAI"
        raw_key = st.text_input("API Key", type="password", help=key_help)
        user_api_key = raw_key.strip() if raw_key else ""
        if ai_provider == "自定义":
            user_base_url = st.text_input("Base URL", value=default_base)
            user_model = st.text_input("模型名称", value=default_model)
        else:
            user_base_url = default_base
            user_model = default_model
        if st.button("测试连接", icon=":material/wifi:"):
            if not user_api_key: st.error("请先填写 Key")
            else:
                try:
                    client = OpenAI(api_key=user_api_key, base_url=user_base_url)
                    client.chat.completions.create(model=user_model, messages=[{"role":"user","content":"Hi"}], max_tokens=5)
                    st.success("连接成功")
                except Exception as e: st.error(f"失败: {e}")
        ai_config_pack = {'key': user_api_key, 'base': user_base_url, 'model': user_model} if user_api_key else None

    st.markdown("---")
    select_date = st.date_input("日期", date.today(), key="date_picker")
    
    # 自动回填
    if st.session_state.last_selected_date != select_date:
        st.session_state.last_selected_date = select_date
        st.session_state.reading_list = [] 
        defaults = {col: "" for col in ALL_COLUMNS}
        defaults['初始状态'] = 60; defaults['结算状态'] = 80
        for col in COLS_CHECKS: defaults[col] = False
        default_time_obj = datetime.now().time().replace(second=0, microsecond=0)
        df_check = load_data()
        today_found = False
        if not df_check.empty:
            mask = df_check['日期'] == str(select_date)
            if mask.any():
                today_found = True
                row = df_check[mask].iloc[0]
                for col in ALL_COLUMNS:
                    try:
                        val = row[col]
                        if col in ['初始状态', '结算状态'] + COLS_STATS: defaults[col] = float(val) if val and val!='nan' else 0
                        elif col == '阅读数据_JSON' and val and val.strip(): st.session_state.reading_list = json.loads(val)
                        elif col.endswith('_Check'): defaults[col] = True if str(val)=='True' else False
                        else: defaults[col] = str(val) if val and val!='nan' else ""
                    except: pass
                if defaults['具体时间']:
                    try: default_time_obj = datetime.strptime(defaults['具体时间'][:5], "%H:%M").time()
                    except: pass
        if not today_found and not df_check.empty:
            df_past = df_check[df_check['日期_dt'].dt.date < select_date].sort_values('日期', ascending=False)
            if not df_past.empty:
                latest_row = df_past.iloc[0]
                try:
                    lbs = json.loads(latest_row['阅读数据_JSON'])
                    active = [b for b in lbs if not b.get('finish_date')]
                    for b in active: b['note'] = ""
                    if active: st.session_state.reading_list = active; st.toast(f"继承书单 from {latest_row['日期']}")
                except: pass
                defaults['地点'] = latest_row.get('地点', '')
        
        st.session_state.defaults = defaults
        st.session_state.default_time_obj = default_time_obj

    curr_defs = st.session_state.get('defaults', {c: "" for c in ALL_COLUMNS})
    curr_time_obj = st.session_state.get('default_time_obj', datetime.now().time())

    # 封装输入区
    def render_input_area():
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1: 
            default_idx = get_nearest_time_index(curr_time_obj)
            select_time_str = st.selectbox("时间 (晚->早)", TIME_OPTIONS, index=default_idx, key="time_picker")
        with col_t2: st.text_input("温度", value=curr_defs.get('温度',''), placeholder="25℃", key="tmp_input")
        col_e1, col_e2 = st.columns(2)
        with col_e1: st.text_input("地点", value=curr_defs.get('地点',''), key="loc_input")
        with col_e2: 
            # 修复：移除 selectbox 的 index 参数，避免与 key 冲突
            wea_sel = st.selectbox("天气", WEA_OPTS, key="wea_select")
            if wea_sel == '手动输入':
                st.text_input("输入天气", key="wea_manual")
        
        st.markdown("---")
        st.subheader("能量状态")
        s_start = st.slider("起床状态", 0, 100, int(curr_defs.get('初始状态', 60)))
        c_s1, c_s2 = st.columns(2)
        with c_s1: reason_start = st.text_input("感受/原因", value=curr_defs.get('初始_感受',''), key="reason_start")
        with c_s2: action_start = st.text_input("点赞/改善", value=curr_defs.get('初始_点赞',''), key="action_start")
        st.markdown("")
        s_end = st.slider("结算状态", 0, 100, int(curr_defs.get('结算状态', 80)))
        c_e1, c_e2 = st.columns(2)
        with c_e1: reason_end = st.text_input("感受/原因", value=curr_defs.get('结算_感受',''), key="reason_end")
        with c_e2: action_end = st.text_input("点赞/改善", value=curr_defs.get('结算_点赞',''), key="action_end")

        st.markdown("---")
        with st.expander("最近在读 (书籍管理)", expanded=True):
            if not st.session_state.reading_list: st.info("暂无")
            else:
                del_idx = []
                for i, b in enumerate(st.session_state.reading_list):
                    st.markdown(f"**{b['name']}**")
                    c1, c2 = st.columns([2,1])
                    with c1:
                        nc = st.number_input("当前页码", 0, int(b['total']), int(b['current']), key=f"p_{i}_{select_date}")
                        st.session_state.reading_list[i]['current'] = nc
                    with c2:
                        pct = 0
                        if b['total']>0: pct = nc/b['total']
                        st.caption(f"进度: {pct:.1%}")
                    if pct >= 0.9: st.checkbox("标记为已读完 (结算时归档)", key=f"finish_{i}_{select_date}")
                    st.session_state.reading_list[i]['note'] = st.text_area("阅读感悟", b['note'], height=50, key=f"n_{i}_{select_date}")
                    if st.button("移除", key=f"d_{i}", icon=":material/delete:"): del_idx.append(i)
                    st.markdown("---")
                if del_idx:
                    for x in sorted(del_idx, reverse=True): del st.session_state.reading_list[x]
                    st.rerun()
            st.caption("添加新书")
            bn = st.text_input("书名", key="new_b")
            c1, c2 = st.columns(2)
            with c1: bt = st.number_input("总页数", 0, step=1, key="new_t")
            with c2: bc = st.number_input("当前页", 0, step=1, key="new_c")
            if st.button("添加", icon=":material/add:"):
                if bn and bt>0:
                    st.session_state.reading_list.append({"name":bn, "total":bt, "current":bc, "note":""})
                    st.rerun()

        def render_check_input(label, txt_key, chk_key):
            c1, c2 = st.columns([5, 1])
            with c1: t = st.text_area(label, height=68, key=txt_key)
            if t and t.strip(): st.session_state[chk_key] = True
            with c2: 
                st.write(""); st.write("")
                c = st.checkbox("打卡", key=chk_key)
            return t, str(c)

        input_data = {}
        with st.expander("一、晨间复盘", expanded=True):
            input_data['晨_学习'] = st.text_area("学习/输入", height=68, key="mk1")
            input_data['晨_锻炼'], input_data['晨_锻炼_Check'] = render_check_input("锻炼/活动", "mk2", "chk_m_ex")
            input_data['晨_娱乐'], input_data['晨_娱乐_Check'] = render_check_input("娱乐/游戏", "mk3", "chk_m_en")
            input_data['晨_冥想'], input_data['晨_冥想_Check'] = render_check_input("冥想/休息", "mk4", "chk_m_me")
            input_data['晨_反思'] = st.text_area("反思/梳理", height=68, key="mk5")

        with st.expander("二、白天复盘", expanded=True):
            input_data['昼_收获'] = st.text_area("收获/做对", height=68, key="dk1")
            input_data['昼_感受'] = st.text_area("感受/体验", height=68, key="dk2")
            input_data['昼_失误'] = st.text_area("失误/问题", height=68, key="dk3")

        with st.expander("三、晚间复盘", expanded=True):
            input_data['晚_学习'] = st.text_area("学习/输入", height=68, key="nk1")
            input_data['晚_锻炼'], input_data['晚_锻炼_Check'] = render_check_input("锻炼/活动", "nk2", "chk_n_ex")
            input_data['晚_娱乐'], input_data['晚_娱乐_Check'] = render_check_input("娱乐/游戏", "nk3", "chk_n_en")
            input_data['晚_冥想'], input_data['晚_冥想_Check'] = render_check_input("冥想/休息", "nk4", "chk_n_me")
            input_data['晚_反思'] = st.text_area("反思/梳理", height=68, key="nk5")

        st.markdown("---")
        achieve = st.text_input("每日总结 (必填)", placeholder="说说今天...", key="achieve_input")
        
        if st.button("💾 存档 (计算属性)", type="primary", icon=":material/save:"):
            if achieve:
                active_books = []
                finished_books = []
                old_finished = []
                if '已读列表_JSON' in curr_defs and curr_defs['已读列表_JSON']:
                    try: old_finished = json.loads(curr_defs['已读列表_JSON'])
                    except: pass

                for i, book in enumerate(st.session_state.reading_list):
                    if st.session_state.get(f"finish_{i}_{select_date}", False):
                        book['finish_date'] = str(select_date)
                        finished_books.append(book)
                    else:
                        active_books.append(book)
                
                st.session_state.reading_list = active_books
                final_finished = old_finished + finished_books

                bj = json.dumps(active_books, ensure_ascii=False)
                fbj = json.dumps(final_finished, ensure_ascii=False)

                final_d = {
                    '日期': select_date, '具体时间': str(select_time_str), '地点': st.session_state.loc_input, 
                    '天气': st.session_state.wea_manual if st.session_state.wea_select == '手动输入' else st.session_state.wea_select, 
                    '温度': st.session_state.tmp_input,
                    '初始状态': s_start, '结算状态': s_end, 
                    '初始_感受': reason_start, '初始_点赞': action_start,
                    '结算_感受': reason_end,   '结算_点赞': action_end,
                    '阅读数据_JSON': bj, '已读列表_JSON': fbj, '每日总结': achieve, **input_data
                }
                
                if save_record(final_d, ai_config_pack):
                    st.success("✅ 存档成功")
                    if finished_books: st.balloons()
                    st.rerun()
            else:
                st.warning("请填写【每日总结】")

# --- 4. 主页面 ---
st.title("角色属性面板")

df = load_data()
if df.empty: st.info("请先在左侧建立第一个存档")
else:
    try:
        df['日期'] = pd.to_datetime(df['日期'])
        num_cols = ['初始状态', '结算状态'] + COLS_STATS
        for c in num_cols: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df = df.sort_values('日期')
    except: pass

    tab0, tab1, tab2, tab3, tab4 = st.tabs(["📝 每日复盘", "📊 属性看板", "🗺️ 冒险记录", "🔮 灵魂之镜", "🏛️ 皇家宝库"])

    # === Tab 0: 每日复盘 (输入区) ===
    with tab0:
        render_input_area()

    # === Tab 1: 属性看板 ===
    with tab1:
        all_cards = []
        for _, r in df.iterrows():
            try: all_cards.extend(json.loads(r.get('卡牌掉落_JSON', '[]')))
            except: pass
        unique_card_ids = set(c['id'] for c in all_cards)
        bonus_exp = 100 if len(unique_card_ids) >= 78 else 0

        total_stats = {
            "智慧 (INT)": df['属性_智慧'].sum(), "体质 (STR)": df['属性_体质'].sum(),
            "心力 (MEN)": df['属性_心力'].sum(), "意志 (WIL)": df['属性_意志'].sum(),
            "魅力 (CHA)": df['属性_魅力'].sum()
        }
        total_exp = float(sum(total_stats.values())) + bonus_exp
        
        # 称号
        rank_icon = "🌱"
        rank_title = "见习旅者"
        level = 1
        if total_exp < 100: 
            rank_icon = "🌱"; rank_title = "见习旅者"; level = 1
        elif total_exp < 300: 
            rank_icon = "🗡️"; rank_title = "探索者"; level = int(total_exp // 10)
        elif total_exp < 600: 
            rank_icon = "🛡️"; rank_title = "坚毅行者"; level = int(total_exp // 10)
        elif total_exp < 1000: 
            rank_icon = "⚔️"; rank_title = "荣耀勇士"; level = int(total_exp // 10)
        else: 
            rank_icon = "👑"; rank_title = "传奇领主"; level = int(total_exp // 10)
            
        equipped_badge = ""
        try:
            df_sorted = df.sort_values('日期_dt')
            wear_json = df_sorted.iloc[-1].get('佩戴成就_JSON', '{}')
            if not wear_json or wear_json == "nan": wear_json = "{}"
            latest_wear = json.loads(wear_json)
            if latest_wear:
                equipped_badge = f" · <span class='badge-worn'>{latest_wear['icon']} {latest_wear['name']}</span>"
        except: pass
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"### Lv.{level} {rank_icon} {rank_title}{equipped_badge}", unsafe_allow_html=True)
            st.caption(f"总经验: {total_exp:.1f}")
            st.progress(min(1.0, (total_exp % 100) / 100))
            
            if HAS_PLOTLY:
                fig = go.Figure(data=go.Scatterpolar(
                    r=list(total_stats.values()), theta=list(total_stats.keys()), fill='toself', name='属性'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=False, margin=dict(t=20, b=20, l=20, r=20), height=300)
                st.plotly_chart(fig, use_container_width=True)
        
        today_diff = {k: 0 for k in ["智慧", "体质", "心力", "意志", "魅力"]}
        mask = df['日期'].dt.strftime('%Y-%m-%d') == str(select_date)
        if mask.any():
            row = df[mask].iloc[0]
            for k in today_diff.keys():
                today_diff[k] = float(row.get(f'属性_{k}', 0))

        total_days = len(df) if len(df) > 0 else 1
        
        # 修复：移除 HTML 标签间的换行和缩进，避免被识别为代码块
        stat_html = '<div class="stat-grid">'
        attr_keys = [("智慧 (INT)", "智慧"), ("体质 (STR)", "体质"), ("心力 (MEN)", "心力"), ("意志 (WIL)", "意志"), ("魅力 (CHA)", "魅力")]
        for full, short in attr_keys:
            val = float(total_stats[full])
            diff = today_diff[short]
            avg = val / total_days
            stat_html += f'<div class="stat-card"><div class="stat-title">{short}</div><div class="stat-value">{val:.1f}</div><div class="stat-delta">{diff:+.1f}</div><div class="stat-avg">日均 {avg:.1f}</div></div>'
        stat_html += "</div>"
        st.markdown(stat_html, unsafe_allow_html=True)

        st.divider()
        
        st.subheader("每日奇遇 (战利品)")
        mask_curr = df['日期'].dt.strftime('%Y-%m-%d') == str(select_date)
        loot = {}; current_cards = []
        if mask.any():
            try: loot = json.loads(df[mask_curr].iloc[0].get('每日奇遇_JSON', '{}'))
            except: pass
            try: current_cards = json.loads(df[mask_curr].iloc[0].get('卡牌掉落_JSON', '[]'))
            except: pass

        if not loot and not current_cards:
            if mask.any(): st.warning("🌫️ 似乎什么都没有发现... (内容过少或无效)")
            else: st.info("📜 尚未书写今日篇章")
        else:
            date_key = str(select_date)
            is_revealed = st.session_state.loot_revealed.get(date_key, False)
            if not is_revealed:
                if st.button("✨ 鉴定今日宝物 ✨", key="reveal_btn"):
                    st.session_state.loot_revealed[date_key] = True
                    st.rerun()
            else:
                if current_cards:
                    st.markdown("#### 🎴 命运指引")
                    cols_c = st.columns(3)
                    for i, card in enumerate(current_cards):
                        card_key = f"card_reveal_{date_key}_{i}"
                        with cols_c[i % 3]:
                            if st.session_state.get(card_key, False):
                                card_meta = next((t for t in TAROT_DATA if t['id'] == card['id']), card)
                                with st.container(border=True):
                                    if card_meta['rarity'] == 'SSR': st.success("✨ 传说降临！")
                                    st.markdown(f"<div class='big-emoji'>{card_meta['icon']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>{card_meta['name']}</div>", unsafe_allow_html=True)
                                    st.info(card_meta['desc'])
                            else:
                                if st.button("🎴 揭开", key=f"btn_{card_key}"):
                                    st.session_state[card_key] = True
                                    st.rerun()
                    st.divider()

                col_l1, col_l2, col_l3 = st.columns(3)
                with col_l1:
                    st.markdown("#### 智慧符文")
                    rune = loot.get('rune', {})
                    st.info(f"**{rune.get('title','')}**\n\n{rune.get('desc','')}")
                    is_c = bool(rune.get('collected', False))
                    st.button("已收藏" if is_c else "收藏", key="c_rune", icon=":material/favorite:", disabled=is_c, on_click=toggle_collection_callback, args=(select_date, 'rune'))
                with col_l2:
                    st.markdown("#### 吟游诗篇")
                    poem = loot.get('poem', {})
                    st.info(f"_{poem.get('content','')}_\n\n—— {poem.get('source','')}")
                    is_c = bool(poem.get('collected', False))
                    st.button("已收藏" if is_c else "收藏", key="c_poem", icon=":material/favorite:", disabled=is_c, on_click=toggle_collection_callback, args=(select_date, 'poem'))
                with col_l3:
                    st.markdown("#### 异闻碎片")
                    trivia = loot.get('trivia', {})
                    st.info(trivia.get('content'))
                    is_c = bool(trivia.get('collected', False))
                    st.button("已收藏" if is_c else "收藏", key="c_trivia", icon=":material/favorite:", disabled=is_c, on_click=toggle_collection_callback, args=(select_date, 'trivia'))

    # === Tab 2: 冒险记录 (详情修复) ===
    with tab2:
        c1, c2, c3, c4 = st.columns(4)
        avg_s = df['初始状态'].mean()
        avg_e = df['结算状态'].mean()
        total_read = 0
        for _, r in df.iterrows():
            try:
                for b in json.loads(r.get('阅读数据_JSON', '[]')):
                    curr = int(b.get('current',0))
                    name = b.get('name','')
                    if name: total_read += curr
            except: pass
            
        c1.metric("登录天数", len(df))
        c2.metric("平均起床HP", f"{avg_s:.0f}")
        c3.metric("平均结算HP", f"{avg_e:.0f}")
        c4.metric("阅读经验", f"{total_read} 页")
        st.divider()

        st.subheader("🗺️ 冒险足迹")
        if not df.empty:
            min_d = df['日期_dt'].min()
            max_d = date(date.today().year, 12, 31)
            all_d = pd.date_range(min_d, max_d).date
            df_full = pd.DataFrame({'日期_dt': pd.to_datetime(all_d)})
            df_chart = df.copy()
            df_chart['Total_HP'] = df_chart['初始状态'].astype(int) + df_chart['结算状态'].astype(int)
            df_merged = pd.merge(df_full, df_chart, on='日期_dt', how='left').fillna(0)
            
            col_y, col_m, col_n1, col_n2 = st.columns([2, 2, 1, 1])
            with col_y: sel_year = st.selectbox("年份", range(2023, 2031), index=st.session_state.view_year - 2023)
            with col_m: sel_month = st.selectbox("月份", range(1, 13), index=st.session_state.view_month - 1)
            if sel_year != st.session_state.view_year: st.session_state.view_year = sel_year; st.rerun()
            if sel_month != st.session_state.view_month: st.session_state.view_month = sel_month; st.rerun()
            
            cal = calendar.Calendar(firstweekday=0)
            month_days = cal.monthdatescalendar(st.session_state.view_year, st.session_state.view_month)
            plot_data = []
            for w_idx, week in enumerate(month_days):
                for d_idx, d_date in enumerate(week):
                    if d_date.month == st.session_state.view_month:
                        hp=0; has=False; d_str=d_date.strftime('%Y-%m-%d')
                        mask=df['日期']==d_str
                        if mask.any():
                            row=df[mask].iloc[0]
                            hp=int(row.get('初始状态',0))+int(row.get('结算状态',0))
                            has=True
                        plot_data.append({'date':d_str, 'day':d_date.day, 'week':w_idx, 'weekday':d_idx, 'hp':hp, 'has':has})
            
            if plot_data:
                df_cal = pd.DataFrame(plot_data)
                click = alt.selection_point(fields=['date'], name='select_date')
                hm = alt.Chart(df_cal).mark_rect().encode(
                    x=alt.X('weekday:O', axis=alt.Axis(labelExpr="['一','二','三','四','五','六','日'][datum.value]", title='')),
                    y=alt.Y('week:O', axis=None),
                    color=alt.condition('datum.has', alt.Color('hp:Q', scale=alt.Scale(scheme='greens'), legend=None), alt.value('#f0f0f0')),
                    tooltip=['date', 'hp']
                ).add_params(click).properties(height=250, width='container')
                
                evt = st.altair_chart(hm, use_container_width=True, on_select="rerun")
                sel_d = None
                if hasattr(evt, "selection") and "select_date" in evt.selection:
                    try: sel_d = evt.selection["select_date"][0].get("date")
                    except: pass
                
                if sel_d:
                    target_d = str(sel_d)
                    mask = df['日期'] == target_d
                    if mask.any():
                        row = df[mask].iloc[0]
                        st.markdown(f"### 📅 {target_d}")
                        
                        def show_section(title, cols):
                            content = []
                            for c in cols:
                                val = row.get(c)
                                if c.endswith('_Check'):
                                    if str(val) == 'True': content.append(f"✅ **{c.replace('_Check','').split('_')[1]}** 已打卡")
                                elif val and str(val) != 'nan':
                                    label = c.split('_')[1] if '_' in c else c
                                    content.append(f"- **{label}**: {val}")
                            
                            if content:
                                st.markdown(f"#### {title}")
                                for line in content: st.write(line)
                                st.divider()
                        
                        show_section("🌅 晨间", COLS_MORNING + ['晨_锻炼_Check', '晨_娱乐_Check', '晨_冥想_Check'])
                        show_section("☀️ 昼间", COLS_DAY)
                        show_section("🌙 晚间", COLS_NIGHT + ['晚_锻炼_Check', '晚_娱乐_Check', '晚_冥想_Check'])

                        st.markdown(f"**🏆 总结**: {row.get('每日总结')}")
                        
                        abyss_json = row.get('深渊凝视_JSON', '{}')
                        try:
                             abyss_data = json.loads(abyss_json)
                             if abyss_data and abyss_data.get('completed'):
                                  st.markdown("---")
                                  st.caption("🌀 深渊记录")
                                  st.write(f"**对象**: {abyss_data.get('boss_name')}")
                                  st.info(f"**回应**: {abyss_data.get('answer')}")
                        except: pass

    # === Tab 3: 灵魂之镜 ===
    with tab3:
        st.header("🔮 灵魂之镜")
        if not (ai_config_pack and ai_config_pack.get('key')): st.warning("请配置 API Key")
        else:
            # 标签展示
            try: latest_tags = json.loads(df.iloc[-1].get('印象标签_JSON', '[]'))
            except: latest_tags = []
            if latest_tags:
                st.caption("🔍 你的印象标签：")
                tags_html = "".join([f"<span class='soul-tag'>{tag}</span>" for tag in latest_tags])
                st.markdown(f"<div class='tag-container'>{tags_html}</div>", unsafe_allow_html=True)

            st.divider()
            
            # 深渊凝视
            today_str = str(date.today())
            mask_today = df['日期'] == today_str
            boss_record = {}
            if mask_today.any():
                try: boss_record = json.loads(df[mask_today].iloc[0].get('深渊凝视_JSON', '{}'))
                except: pass
            
            is_completed = boss_record.get('completed', False)
            has_today_record = mask_today.any()

            if not has_today_record:
                st.info("🔒 请先完成今日复盘，方可开启深渊凝视。")
            else:
                if is_completed:
                    st.success("今日试炼已完成。")
                    with st.expander("📜 回望试炼印记", expanded=True):
                        st.write(f"**对象**: {boss_record.get('boss_name')}")
                        if 'answer' in boss_record: st.info(f"**回应**: {boss_record['answer']}")
                        st.write(f"**评分**: {boss_record.get('score')}")
                        st.write(f"**寄语**: {boss_record.get('comment')}")
                        
                        st.markdown("**🎁 获得奖励**:")
                        rewards = []
                        exp_val = boss_record.get('exp', 0)
                        dist = boss_record.get('exp_distribution', {})
                        if exp_val > 0:
                            if dist:
                                detail_str = "；".join([f"{k}+{v}" for k,v in dist.items()])
                                rewards.append(f"经验 +{exp_val} ({detail_str})")
                            else:
                                rewards.append(f"经验 +{exp_val}")
                        if boss_record.get('card'):
                            c = boss_record['card']
                            rewards.append(f"卡牌 [{c['rarity']}] {c['name']} (幸运倍率 x{boss_record.get('mult', 1.0):.1f})")
                        if boss_record.get('modify_tag'):
                            m = boss_record['modify_tag']
                            rewards.append(f"标签变更: {m['old']} -> {m['new']}")
                        if boss_record.get('remove_tag'):
                            rewards.append(f"标签移除: {boss_record['remove_tag']}")
                        if boss_record.get('add_tag'):
                            rewards.append(f"标签获得: {boss_record['add_tag']}")
                        for r in rewards: st.text(f"- {r}")
                
                elif st.session_state.get('boss_result'):
                    res = st.session_state.boss_result
                    st.markdown("### 🎁 战利品鉴定")
                    st.markdown(f"<div class='reward-box'><div>意志评分：{res['score']}</div></div>", unsafe_allow_html=True)
                    
                    exp_dist = res.get('exp_distribution', {})
                    if exp_dist:
                         st.write("🌟 **属性提升**：")
                         cols_exp = st.columns(len(exp_dist))
                         for idx, (k, v) in enumerate(exp_dist.items()):
                              with cols_exp[idx]:
                                   st.metric(k, f"+{v}")
                    
                    st.info(f"**智者寄语**：{res['comment']}")
                    if not st.session_state.get('boss_card_revealed'):
                        if res['card']:
                            if st.button("🎴 翻开命运之牌", type="primary"):
                                st.session_state.boss_card_revealed = True
                                st.rerun()
                        else:
                            st.caption("（本次评分过低，命运之轮未曾转动）")
                            if st.button("结束试炼"):
                                st.session_state.boss_card_revealed = True
                                st.rerun()
                    else:
                        if res['card']:
                            c = res['card']
                            st.markdown(f"<div class='big-emoji'>{c['icon']}</div>", unsafe_allow_html=True)
                            st.markdown(f"**{c['name']}** ({c['rarity']})")
                        if st.button("✨ 确认收下奖励 ✨", type="primary"):
                            try:
                                df_curr = load_data()
                                idx = df_curr[df_curr['日期'] == today_str].index[0]
                                df_curr.at[idx, '深渊凝视_JSON'] = json.dumps(res, ensure_ascii=False)
                                
                                dist = res.get('exp_distribution', {})
                                if not dist and res['exp']>0: dist={'意志': res['exp']}
                                for k,v in dist.items():
                                    col_k = f"属性_{k}"
                                    if col_k in df_curr.columns:
                                        df_curr.at[idx, col_k] = float(df_curr.at[idx, col_k] or 0) + v
                                
                                if res['card']:
                                    cards = json.loads(df_curr.at[idx, '卡牌掉落_JSON'] or '[]')
                                    cards.append(res['card'])
                                    df_curr.at[idx, '卡牌掉落_JSON'] = json.dumps(cards, ensure_ascii=False)

                                raw_tags = df_curr.at[idx, '印象标签_JSON'] or '[]'
                                curr_tags = json.loads(raw_tags)
                                if res.get('modify_tag'):
                                    m = res['modify_tag']
                                    if m['old'] in curr_tags:
                                        curr_tags.remove(m['old']); curr_tags.append(m['new'])
                                if res.get('remove_tag') and res['remove_tag'] in curr_tags:
                                    curr_tags.remove(res['remove_tag'])
                                if res.get('add_tag'): curr_tags.append(res['add_tag'])
                                df_curr.at[idx, '印象标签_JSON'] = json.dumps(curr_tags, ensure_ascii=False)

                                if '日期_dt' in df_curr.columns: del df_curr['日期_dt']
                                df_curr.to_csv(FILE_NAME, index=False, encoding='utf-8-sig')
                                st.session_state.boss_result = None
                                st.session_state.boss_card_revealed = False
                                st.balloons()
                                st.rerun()
                            except: st.error("存档失败")
                
                elif st.session_state.get('boss_battle'):
                    boss = st.session_state.boss_battle
                    theme = "boss-container-truth" if boss.get('type')=='truth' else "boss-container-demon"
                    title_c = "boss-title-truth" if boss.get('type')=='truth' else "boss-title-demon"
                    icon = '🦉' if boss.get('type')=='truth' else '👹'
                    name = "真理追问" if boss.get('type')=='truth' else "试炼挑战"
                    
                    st.markdown(f"""
                    <div class="{theme}">
                        <div class="{title_c}">{icon} {boss.get('name')}</div>
                        <p><em>{boss.get('intro')}</em></p>
                        <hr>
                        <h3>⚔️ {name}：{boss.get('question')}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    ans = st.text_area("你的回应 (真诚面对，理性思考)", height=100, key="boss_ans")
                    if st.button("进行回应", type="primary", icon=":material/send:"):
                        if len(ans)<15: st.warning("回答太短（至少15字）")
                        else:
                            with st.spinner("正在判定..."):
                                res = resolve_boss_battle(boss['question'], ans, ai_config_pack, boss.get('type'))
                                if res:
                                    score = res.get('score', 0)
                                    raw_exp = 0
                                    if score >= 60: raw_exp = 1.0
                                    if score >= 80: raw_exp = 2.0
                                    if score >= 95: raw_exp = 2.5
                                    
                                    card, mult = draw_boss_card(score)
                                    st.session_state.boss_result = {
                                        "boss_name": boss.get('name'), "question": boss.get('question'),
                                        "answer": ans, "score": score, "comment": res.get('comment'),
                                        "exp": raw_exp, "exp_distribution": res.get('exp_distribution'),
                                        "card": card, "mult": mult,
                                        "modify_tag": res.get('modify_tag'), "remove_tag": res.get('remove_tag'),
                                        "add_tag": res.get('add_tag'), "completed": True
                                    }
                                    st.session_state.boss_battle = None
                                    st.rerun()
                else:
                    if st.button("🔥 召唤今日心魔 / 寻求真理", type="primary"):
                        with st.spinner("正在凝视深渊..."):
                            active_books = st.session_state.reading_list
                            boss_data = generate_boss_encounter(df, ai_config_pack, active_books)
                            if boss_data:
                                st.session_state.boss_battle = boss_data
                                st.rerun()

    # === Tab 4: 皇家宝库 (UI 修复) ===
    with tab4:
        st.header("皇家宝库")
        
        # 1. 成就 (折叠)
        with st.expander("🏆 成就勋章", expanded=False):
             unlocked = check_and_unlock_achievements(df)
             u_ids = [a['id'] for a in unlocked]
             try:
                 df_s = df.sort_values('日期_dt')
                 curr_w = json.loads(df_s.iloc[-1].get('佩戴成就_JSON', '{}'))
                 curr_name = curr_w.get('name', '')
             except: curr_name = ""
             
             # 修复：使用 Grid 布局
             ach_html = '<div class="stat-grid">'
             for ach in ACHIEVEMENT_DATA:
                 is_u = ach['id'] in u_ids
                 opacity = "1.0" if is_u else "0.3"
                 filter_style = "" if is_u else "filter: grayscale(100%);"
                 ach_html += f'<div class="stat-card" style="opacity: {opacity}; {filter_style}"><div style="font-size: 24px;">{ach["icon"]}</div><div style="font-size: 10px; font-weight: bold;">{ach["name"]}</div><div style="font-size: 8px; color: #666;">{ach["desc"]}</div></div>'
             ach_html += "</div>"
             st.markdown(ach_html, unsafe_allow_html=True)
             
             if unlocked:
                 st.divider()
                 st.caption("选择佩戴：")
                 cols = st.columns(4)
                 for i, ach in enumerate(unlocked):
                     with cols[i % 4]:
                         if st.button(f"{ach['icon']} {ach['name']}", key=f"wear_{ach['id']}"):
                             equip_badge_callback(json.dumps({"name": ach['name'], "icon": ach['icon']}, ensure_ascii=False))

        # 2. 塔罗图鉴 (折叠)
        with st.expander("🎴 命运图鉴", expanded=False):
            collected_cards = []
            for _, r in df.iterrows():
                try: collected_cards.extend(json.loads(r.get('卡牌掉落_JSON', '[]')))
                except: pass
            
            card_counts = {i: 0 for i in range(78)}
            for c in collected_cards:
                cid = c.get('id')
                if cid is not None: card_counts[cid] += 1
            
            t1, t2, t3, t4, t5 = st.tabs(["大阿卡纳", "权杖", "圣杯", "宝剑", "星币"])
            
            def render_gallery_tab(group_name, container):
                group_cards = [c for c in TAROT_DATA if c.get('group','').startswith(group_name)]
                with container:
                    cols = st.columns(4)
                    for i, card in enumerate(group_cards):
                        cid = card['id']
                        count = card_counts.get(cid, 0)
                        with cols[i % 4]:
                            with st.container(border=True):
                                if count > 0:
                                    st.markdown(f"<div class='tarot-roman'>{card['roman']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div class='big-emoji'>{card['icon']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div class='tarot-cn'>{card['name']}</div>", unsafe_allow_html=True)
                                    st.caption(f"{card['en']}")
                                    st.caption(f"{card['rarity']} | x{count}")
                                    with st.popover("详情"):
                                         st.write(card['desc'])
                                else:
                                    st.markdown(f"<div style='font-size:40px; text-align:center; color:#eee;'>🔒</div>", unsafe_allow_html=True)
                                    st.caption("未解锁")

            render_gallery_tab("大阿卡纳", t1)
            render_gallery_tab("权杖", t2)
            render_gallery_tab("圣杯", t3)
            render_gallery_tab("宝剑", t4)
            render_gallery_tab("星币", t5)
        
        # 3. 智慧典藏 (时光卷轴)
        with st.expander("🏛️ 智慧典藏", expanded=True):
            c1, c2, c3 = st.columns(3)
            
            def get_grouped_loot(loot_type):
                groups = {}
                for _, r in df.sort_values('日期', ascending=False).iterrows():
                    try:
                        loot = json.loads(r.get('每日奇遇_JSON', '{}'))
                        item = loot.get(loot_type, {})
                        if item.get('collected'):
                            ym = r['日期'][:7]
                            if ym not in groups: groups[ym] = []
                            groups[ym].append((r['日期'], item))
                    except: pass
                return groups
            
            def render_column(col, title, type_key):
                with col:
                    st.markdown(f"#### {title}")
                    groups = get_grouped_loot(type_key)
                    if not groups:
                        st.caption("暂无")
                    else:
                        is_first = True
                        for ym, items in groups.items():
                            with st.expander(f"📂 {ym}", expanded=is_first):
                                is_first = False
                                for d, item in items:
                                    with st.container(border=True):
                                        if type_key == 'rune':
                                            st.markdown(f"**{item.get('title')}**")
                                            st.info(item.get('desc'))
                                        elif type_key == 'poem':
                                            st.markdown(f"_{item.get('content')}_")
                                            st.caption(f"—— {item.get('source')}")
                                        else:
                                            st.write(item.get('content'))
                                        
                                        st.caption(f"📅 {d}")
                                        if st.button("移除", key=f"rm_{type_key}_{d}"): toggle_collection_callback(d, type_key)

            render_column(c1, "🔮 符文", "rune")
            render_column(c2, "📜 诗篇", "poem")
            render_column(c3, "🧩 异闻", "trivia")