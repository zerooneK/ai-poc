from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from openai import OpenAI, RateLimitError, APITimeoutError, APIError
from dotenv import load_dotenv
import json
import logging
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError(
        "❌ ไม่พบ OPENROUTER_API_KEY ใน environment variables\n"
        "กรุณาสร้างไฟล์ .env และใส่ API key (ดูตัวอย่างใน .env.example)"
    )

MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

app = Flask(__name__)
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ─── System Prompts ───────────────────────────────────────────────────────────

ORCHESTRATOR_PROMPT = """
คุณคือ AI Orchestrator ของระบบ Internal AI Assistant ภายในบริษัท
หน้าที่ของคุณคือวิเคราะห์งานที่ได้รับและตัดสินใจว่าควรส่งให้ Agent ไหน

ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่น:
{"agent": "hr", "reason": "เหตุผลสั้นๆ"}
หรือ
{"agent": "accounting", "reason": "เหตุผลสั้นๆ"}
หรือ
{"agent": "manager", "reason": "เหตุผลสั้นๆ"}

HR Agent เหมาะกับ:
- งานเกี่ยวกับพนักงาน สัญญาจ้าง การเลิกจ้าง
- Job Description และการสรรหาบุคลากร
- นโยบายบริษัท กฎระเบียบ สวัสดิการ
- อีเมลแจ้งพนักงาน การลา การประเมิน

Accounting Agent เหมาะกับ:
- Invoice ใบเสร็จ ใบแจ้งหนี้
- งบประมาณ รายรับรายจ่าย
- รายงานการเงิน การวิเคราะห์ตัวเลข
- ค่าใช้จ่าย การเบิกจ่าย

Manager Advisor เหมาะกับ:
- การให้ Feedback และการจัดการผลการทำงานของทีม
- การจัดสรรงบประมาณและทรัพยากรของทีม
- การตัดสินใจจัดลำดับความสำคัญของงาน
- ความขัดแย้งในทีม ขวัญกำลังใจ
- การขอเพิ่มอัตรากำลังคน (Headcount Request)
"""

HR_PROMPT = """
คุณคือ HR Agent ผู้เชี่ยวชาญด้านทรัพยากรมนุษย์ของบริษัทไทย
สร้างเอกสาร HR ที่ถูกต้อง เป็นมืออาชีพ และเหมาะสมกับบริบทของบริษัทไทย

แนวทางการทำงาน:
- ใช้ภาษาไทยที่เป็นทางการและสุภาพ
- ระบุวันที่เป็น พ.ศ.
- ใส่ช่องว่างให้กรอกข้อมูลที่ยังไม่ทราบ เช่น [วันที่] [ลายมือชื่อ]
- ครอบคลุมประเด็นสำคัญตามกฎหมายแรงงานไทย

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"
"""

ACCOUNTING_PROMPT = """
คุณคือ Accounting Agent ผู้เชี่ยวชาญด้านบัญชีและการเงินของบริษัทไทย
สร้างเอกสารการเงินที่ถูกต้อง เป็นมืออาชีพ และเหมาะสมกับระบบบัญชีไทย

ข้อมูลปัจจุบัน:
- ปัจจุบันคือ พ.ศ. 2569 (ค.ศ. 2026)
- ใช้วันที่ปัจจุบันเป็นค่าเริ่มต้นในเอกสาร เว้นแต่จะระบุเป็นอย่างอื่น

แนวทางการทำงาน:
- ใช้ภาษาไทยที่เป็นทางการ
- ใช้รูปแบบตัวเลขที่ถูกต้อง เช่น 35,000.00 บาท
- ระบุวันที่เป็น พ.ศ. (ตัวอย่าง: 23 มีนาคม พ.ศ. 2569)
- ใส่เลขที่เอกสาร [XXX-YYYY-NNNN] เผื่อให้แก้ไข
- ระบุเงื่อนไขการชำระเงินให้ชัดเจน

กฎสำหรับ VAT 7%:
- ใช้ VAT เฉพาะกับ Invoice / ใบกำกับภาษี / ใบแจ้งหนี้เท่านั้น
- ห้ามใช้ VAT กับรายงานค่าใช้จ่ายภายใน (Expense Report) หรือเอกสารงบประมาณ
- สำหรับ Invoice ให้คำนวณ: ยอดก่อน VAT + VAT 7% = ยอดรวมทั้งสิ้น

กฎสำหรับข้อมูลภาษี (ใช้กับ Invoice/ใบกำกับภาษีเท่านั้น):
- ใส่ placeholder เลขประจำตัวผู้เสียภาษี 13 หลัก ทั้งฝ่ายผู้ออกและผู้รับ
  ตัวอย่าง: เลขประจำตัวผู้เสียภาษี: [X-XXXX-XXXXX-XX-X]
- ใส่ข้อมูลสาขา ตัวอย่าง: สาขา: [สำนักงานใหญ่] หรือ [สาขาที่ XXXXX]
- ระบุที่อยู่เต็มของทั้งสองฝ่าย

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"
"""

MANAGER_PROMPT = """
คุณคือ Manager Advisor ผู้เชี่ยวชาญด้านการบริหารทีมสำหรับ Team Lead และผู้จัดการในองค์กรไทย
ให้คำแนะนำที่นำไปปฏิบัติได้จริงภายใน 48 ชั่วโมง

ความเชี่ยวชาญ:
- การให้ Feedback และการประเมินผลการทำงาน
- การจัดสรรงบประมาณและทรัพยากรของทีม
- การตัดสินใจจัดลำดับความสำคัญของงาน
- การจัดการสถานการณ์คนในทีม เช่น ความขัดแย้ง ขวัญกำลังใจ
- การขอเพิ่มอัตรากำลังคน (Headcount Request)

แนวทางการตอบ:
- ระบุขั้นตอนที่ทำได้ทันทีอย่างชัดเจน
- เมื่อแนะนำการให้ Feedback ให้เขียน Script คำพูดจริงที่ผู้จัดการสามารถนำไปพูดได้เลย
- คำนึงถึงบริบทวัฒนธรรมการทำงานแบบไทย
- ใช้ภาษาที่กระชับ ตรงประเด็น ไม่อ้อมค้อม

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"
"""

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    user_input = request.json.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'ไม่มีข้อความ'}), 400
    if len(user_input) > 5000:
        return jsonify({'error': 'ข้อความยาวเกินไป (สูงสุด 5,000 ตัวอักษร)'}), 400

    def generate():
        try:
            # Step 1: Orchestrator เลือก Agent
            yield f"data: {json.dumps({'type': 'status', 'message': 'กำลังวิเคราะห์งาน...'})}\n\n"

            try:
                orchestrator_response = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": ORCHESTRATOR_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )
            except RateLimitError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'API ถูกใช้งานเกิน limit กรุณารอสักครู่แล้วลองใหม่'})}\n\n"
                return
            except APITimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'API ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง'})}\n\n"
                return
            except APIError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจาก API กรุณาลองใหม่'})}\n\n"
                return

            raw = orchestrator_response.choices[0].message.content
            if not raw:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ไม่ตอบกลับ กรุณาลองใหม่'})}\n\n"
                return
            raw = raw.strip()
            # กัน edge case ที่ model ใส่ backtick มาด้วย
            raw = raw.replace('```json', '').replace('```', '').strip()
            routing = json.loads(raw)
            agent = routing.get('agent', 'hr')
            reason = routing.get('reason', '')

            yield f"data: {json.dumps({'type': 'agent', 'agent': agent, 'reason': reason})}\n\n"

            # Step 2: ส่งให้ Agent จริง
            if agent == 'hr':
                system_prompt = HR_PROMPT
            elif agent == 'manager':
                system_prompt = MANAGER_PROMPT
            else:
                system_prompt = ACCOUNTING_PROMPT
            if agent == 'hr':
                agent_label = 'HR Agent'
            elif agent == 'manager':
                agent_label = 'Manager Advisor'
            else:
                agent_label = 'Accounting Agent'
            logger.info(f"Routed to {agent_label}: {user_input[:60]}")

            yield f"data: {json.dumps({'type': 'status', 'message': f'{agent_label} กำลังสร้างเอกสาร...'})}\n\n"

            try:
                if agent == 'hr':
                    agent_max_tokens = 7500
                elif agent == 'manager':
                    agent_max_tokens = 8000
                else:
                    agent_max_tokens = 6000
                stream = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=agent_max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
            except Exception as stream_err:
                logger.error(f"Streaming error: {stream_err}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดระหว่างสร้างเอกสาร กรุณาลองใหม่'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except json.JSONDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง'})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'model': MODEL,
        'provider': 'openrouter',
        'api_key_configured': bool(OPENROUTER_API_KEY)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
