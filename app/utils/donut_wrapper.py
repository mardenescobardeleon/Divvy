# app/utils/donut_wrapper.py
from transformers import VisionEncoderDecoderModel, DonutProcessor
from app.utils.image_helpers import preprocess_receipt
from PIL import Image
import torch
import json
import re

class DonutOCR:
    def __init__(self):
        # print("⏳ Loading Donut model...")
        # # self.processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-rvlcdip")
        # # self.model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-rvlcdip")
        # self.processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
        # self.model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
        # self.model.eval()
        # print("✅ Donut loaded.")

        print("⏳ Loading Donut CORD-v2 model…")
        self.processor = DonutProcessor.from_pretrained(
            "naver-clova-ix/donut-base-finetuned-cord-v2"
        )
        self.model = VisionEncoderDecoderModel.from_pretrained(
            "naver-clova-ix/donut-base-finetuned-cord-v2"
        )
        # send to GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        print("✅ Donut CORD-v2 loaded.")

    def extract_receipt_data(self, image_path):
        # image = Image.open(image_path).convert("RGB")
        # pixel_values = self.processor(image, return_tensors="pt").pixel_values

        # with torch.no_grad():
        #     outputs = self.model.generate(pixel_values, max_length=512, num_beams=1)

        # decoded = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        # print("🔍 [DonutOCR] raw decoded string:", repr(decoded))
        # return json.loads(decoded)
        # 1) load & preprocess
        img = Image.open(image_path).convert("RGB")
        pixel_values = self.processor(img, return_tensors="pt").pixel_values.to(self.device)

        # 2) prepare the CORD‐v2 prompt token
        # schema = """
        #     Produce JSON in this exact form:
        #     {
        #     "items": [
        #         { "name": "<item name>", "quantity": <integer>, "price": <float> },
        #         …
        #     ],
        #     "sub_total": <float>,
        #     "total": <float>
        #     }
        #     Only include real line‐items. Omit headers/footers.
        # """
        # task_prompt = "<s_cord-v2><s_text>"+schema+"</s_text>"
        instruction = '''<s_cord-v2>
        <s_task>
        Parse this receipt image and output a JSON object with exactly the following fields:
        {
        "line_items": [
            {
            "name": "ITEM_NAME",
            "quantity": QUANTITY,
            "total": ITEM_TOTAL
            },
            …
        ],
        "sub_total": SUBTOTAL,
        "service_fee": SERVICE_FEE_OR_0,
        "tax": TAX_OR_0,
        "tip": TIP_OR_0,
        "total": TOTAL
        }
        Only include real purchased items (food/products) in `line_items`—exclude restaurant name, address, phone, and other metadata.
        If `service_fee`, `tax`, or `tip` are missing on the receipt, set their value to 0.
        Return **only** the JSON, with no extra text or formatting.
        </s_task>'''.strip()

        
        decoder_input_ids = self.processor.tokenizer(
          instruction, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self.device)

        # 3) generate
        with torch.no_grad():
            outputs = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.model.config.decoder.max_position_embeddings,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=5,
                bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )

        # 4) decode & strip off the prompt tag
        sequence = self.processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
        # remove the leading <s_cord-v2> and any trailing tags
        sequence = re.sub(r"^<s_cord-v2>(.*)</s_cord-v2>$", r"\1", sequence).strip()

        # 5) convert token sequence to JSON
        # This uses DonutProcessor.token2json under the hood to handle nested tags
        parsed = self.processor.token2json(sequence)
        return parsed
