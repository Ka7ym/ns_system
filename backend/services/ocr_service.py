import datetime
import io
import os
import re
from typing import Optional

from config import load_app_settings

UNRECOGNIZED = "Поле не распознано"

IIN_RE = re.compile(r"(?<![A-ZА-Аа,Әә,Бб,Вв,Гг,Ғғ,Дд,Ее,Ёё,Жж,Зз,Ии,Йй,Кк,Ққ,Лл,Мм,Нн,Ңң,Оо,Өө,Пп,Рр,Сс,Тт,Уу,Ұұ,Үү,Фф,Хх,Һһ,Цц,Чч,Шш,Щщ,Ъъ,Ыы,Іі,Ьь,Ээ,Юю,Яя])\d(?:[\s\-.:|]?\d){11}(?![A-ZА-Аа,Әә,Бб,Вв,Гг,Ғғ,Дд,Ее,Ёё,Жж,Зз,Ии,Йй,Кк,Ққ,Лл,Мм,Нн,Ңң,Оо,Өө,Пп,Рр,Сс,Тт,Уу,Ұұ,Үү,Фф,Хх,Һһ,Цц,Чч,Шш,Щщ,Ъъ,Ыы,Іі,Ьь,Ээ,Юю,Яя])", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{2}[./]\d{2}[./]\d{4}|\d{4}-\d{2}-\d{2})\b")
DOC_NO_RE = re.compile(r"\b([A-ZА-Я]{0,2}\d{8,12})\b", re.IGNORECASE)
IIN_OCR_CHARS = str.maketrans({
    "O": "0", "o": "0", "Q": "0", "q": "0", "О": "0", "о": "0", "Ө": "0", "ө": "0",
    "I": "1", "i": "1", "L": "1", "l": "1", "І": "1", "і": "1", "|": "1",
    "Z": "2", "z": "2", "З": "3", "з": "3", "S": "5", "s": "5", "В": "8", "в": "8",
})
SERVICE_WORDS = {
    "республика",
    "respublikasy",
    "қазақстан",
    "казахстан",
    "qazaqstan",
    "жеке",
    "куәлік",
    "куәлiк",
    "удостоверение",
    "identity",
    "card",
    "document",
}
NAME_LABELS = (
    "фамилия", "тегі", "тегi", "имя", "аты", "отчество",
    "әкесінің аты", "әкесiнiң аты", "әке аты",
    "фио", "full name", "name", "surname", "given name", "last name",
)
SURNAME_LABEL = re.compile(r"(?:фамилия|тегі|тегi|surname|family\s*name|last\s*name)", re.IGNORECASE)
GIVEN_NAME_LABEL = re.compile(r"(?:имя|аты|given\s*name|name)", re.IGNORECASE)
PATRONYMIC_LABEL = re.compile(r"(?:отчество|әкесінің\s+аты|әке\s+аты|patronymic|middle\s*name)", re.IGNORECASE)
NAME_LABEL_RE = re.compile(
    r"(?:фамилия|тегі|тегi|имя|аты|отчество|фио|full\s*name|name|surname|family\s*name|last\s*name|given\s*name|әкесінiң\s+аты|әке\s+аты)",
    re.IGNORECASE,
)
EXPIRY_LABELS = (
    "мерзімі",  "мерзімі",
    "срок действия", "действителен", "valid until",
    "expiry", "expiration", "validity", "date of expiry",
)


class OcrProvider:
    def process(self, file_bytes: bytes, mime: str, filename: str) -> dict:
        raise NotImplementedError


class TesseractOcrProvider(OcrProvider):
    def _configure(self) -> tuple[bool, str]:
        settings = load_app_settings()
        cmd = (settings.get("tesseract_cmd") or "").strip()
        try:
            import pytesseract
        except ImportError:
            return False, "OCR требует настройки: пакет pytesseract не установлен"

        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        else:
            project_tesseract = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "tools",
                "tesseract",
                "tesseract.exe",
            )
            for candidate in (
                project_tesseract,
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "tesseract",
            ):
                if candidate == "tesseract" or os.path.exists(candidate):
                    pytesseract.pytesseract.tesseract_cmd = candidate
                    break
        try:
            pytesseract.get_tesseract_version()
            return True, ""
        except Exception:
            return False, "OCR требует настройки: установите Tesseract OCR на сервер"

    def _image_from_bytes(self, file_bytes: bytes, mime: str, filename: str):
        from PIL import Image, ImageOps

        name = (filename or "").lower()
        if mime == "application/pdf" or name.endswith(".pdf"):
            try:
                import pypdfium2 as pdfium

                pdf = pdfium.PdfDocument(file_bytes)
                return [pdf[index].render(scale=3).to_pil() for index in range(min(len(pdf), 4))]
            except Exception:
                return []
        try:
            return [ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("RGB")]
        except Exception:
            return []

    def _preprocess(self, image):
        from PIL import ImageEnhance, ImageFilter, ImageOps

        image = ImageOps.exif_transpose(image).convert("L")
        max_dimension = max(image.size)
        if max_dimension < 2200:
            scale = 2200 / max_dimension
            image = image.resize((int(image.width * scale), int(image.height * scale)))
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(1.6)
        image = ImageEnhance.Sharpness(image).enhance(1.7)
        return image.filter(ImageFilter.MedianFilter(size=3))

    def _preprocess_variants(self, image):
        from PIL import ImageEnhance, ImageOps

        enhanced = self._preprocess(image)
        threshold = enhanced.point(lambda value: 255 if value > 160 else 0)
        high_contrast = ImageEnhance.Contrast(enhanced).enhance(2.2)
        return (enhanced, threshold, high_contrast)

    def _ocr_language(self) -> str:
        import pytesseract

        try:
            available = set(pytesseract.get_languages(config=""))
        except Exception:
            return "kaz+rus+eng"
        if {"kaz", "rus", "eng"}.issubset(available):
            return "kaz+rus+eng"
        if {"kaz", "rus", "eng"}.issubset(available):
            return "rus+eng"
        return "+".join(language for language in ("rus","kaz","eng") if language in available) or "eng"

    def process(self, file_bytes: bytes, mime: str, filename: str) -> dict:
        empty = {
            "full_name": {"value": None, "recognized": False},
            "iin": {"value": None, "recognized": False},
            "birth_date": {"value": None, "recognized": False},
            "document_number": {"value": None, "recognized": False},
            "document_issue_date": {"value": None, "recognized": False},
            "document_expiry_date": {"value": None, "recognized": False},
        }
        ok, message = self._configure()
        if not ok:
            return {
                "status": "ocr_not_configured",
                "message": message,
                "fields": empty,
                "raw_text": None,
            }

        import pytesseract

        images = self._image_from_bytes(file_bytes, mime, filename)
        if not images:
            return {
                "status": "failed",
                "message": "Не удалось прочитать файл для распознавания",
                "fields": empty,
                "raw_text": None,
            }

        language = self._ocr_language()
        texts = []
        iin_word_candidates: list[tuple[str, int]] = []
        for image in images:
            for variant in self._preprocess_variants(image):
                for psm in (6, 11, 12):
                    try:
                        text = pytesseract.image_to_string(
                            variant,
                            lang=language,
                            config=f"--oem 3 --psm {psm} -c preserve_interword_spaces=1",
                        )
                        if text.strip():
                            texts.append(text)
                        if psm == 11:
                            data = pytesseract.image_to_data(
                                variant,
                                lang=language,
                                config="--oem 3 --psm 11",
                                output_type=pytesseract.Output.DICT,
                            )
                            for token, confidence in zip(data["text"], data["conf"]):
                                digits = re.sub(r"\D", "", token.translate(IIN_OCR_CHARS))
                                try:
                                    token_confidence = int(float(confidence))
                                except (TypeError, ValueError):
                                    continue
                                if len(digits) == 12 and token_confidence >= 45:
                                    iin_word_candidates.append((digits, token_confidence))
                    except Exception:
                        continue
        raw = max(texts, key=self._recognized_score, default="")
        if not raw:
            return {
                "status": "failed",
                "message": "Не удалось выполнить распознавание. Проверьте качество изображения.",
                "fields": empty,
                "raw_text": None,
            }

        combined_text = "\n".join(texts)
        parsed = self._parse(raw, additional_text=combined_text, iin_candidates=iin_word_candidates)
        recognized_count = sum(1 for item in parsed.values() if item["recognized"])
        status = "ok" if recognized_count else "partial"
        return {
            "status": status,
            "message": "Распознавание завершено. Обязательно проверьте поля." if recognized_count else "Не удалось уверенно распознать поля. Введите данные вручную.",
            "fields": parsed,
            "raw_text": raw[:4000],
            "pages_processed": len(images),
            "ocr_profiles": len(texts),
        }

    def _parse(
        self,
        text: str,
        additional_text: str = "",
        iin_candidates: Optional[list[tuple[str, int]]] = None,
    ) -> dict:
        normalized = self._normalize_ocr_text(text)
        combined = "\n".join(part for part in (text, additional_text) if part)
        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        iin, iin_valid, _ = self._extract_iin(combined, iin_candidates)
        dates = DATE_RE.findall(normalized)
        doc_match = DOC_NO_RE.search(normalized.replace(" ", ""))
        full_name, name_confident = self._extract_full_name(lines)

        birth = self._extract_labeled_date(lines, ("туған күні", "туған күні", "дата рождения", "birth date"))
        if not birth:
            birth = dates[0] if dates else None

        issue = None
        expiry = None
        for index, line in enumerate(lines):
            if self._line_has_label(line, ("берілген күні", "берілді", "выдано", "дата выдачи", "берілген күні / срок действия", "дата выдачи / срок действия")):
                candidates = DATE_RE.findall(line)
                if not candidates and index + 1 < len(lines):
                    candidates = DATE_RE.findall(lines[index + 1])
                if len(candidates) >= 2:
                    issue = candidates[0]
                    expiry = candidates[-1]
                elif candidates:
                    issue = candidates[0]
            if self._line_has_label(line, EXPIRY_LABELS):
                candidates = DATE_RE.findall(line)
                if not candidates and index + 1 < len(lines):
                    candidates = DATE_RE.findall(lines[index + 1])
                if len(candidates) >= 2:
                    issue = candidates[0]
                    expiry = candidates[-1]
                elif candidates:
                    expiry = candidates[-1]

        if issue is None and expiry is not None and dates:
            issue = dates[0]

        unlabelled_dates = [date for date in dates if date != birth]
        if issue is None and unlabelled_dates:
            issue = unlabelled_dates[0]
        if expiry is None and len(unlabelled_dates) > 1:
            expiry = unlabelled_dates[-1]

        issue_date_obj = None
        if issue:
            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    issue_date_obj = datetime.datetime.strptime(issue, fmt).date()
                    break
                except ValueError:
                    continue

        expiry_label_present = any(self._line_has_label(line, EXPIRY_LABELS) for line in lines)
        if issue_date_obj and expiry_label_present and expiry is not None and expiry == issue and len(dates) >= 2:
            try:
                expiry_obj = issue_date_obj.replace(year=issue_date_obj.year + 10)
            except ValueError:
                expiry_obj = datetime.date(issue_date_obj.year + 10, issue_date_obj.month, 1) - datetime.timedelta(days=1)
            expiry = expiry_obj.strftime("%d.%m.%Y")

        def field(value: Optional[str], recognized: Optional[bool] = None) -> dict:
            return {"value": value, "recognized": bool(value) if recognized is None else recognized}

        return {
            "full_name": field(full_name, name_confident),
            "iin": field(iin, iin_valid),
            "birth_date": field(birth),
            "document_number": field(doc_match.group(1) if doc_match else None),
            "document_issue_date": field(issue),
            "document_expiry_date": field(expiry),
        }

    def _normalize_ocr_text(self, text: str) -> str:
        return text.replace("\u00a0", " ").replace("\u200b", " ")

    def _recognized_score(self, text: str) -> int:
        normalized = self._normalize_ocr_text(text)
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        _, iin_valid, _ = self._extract_iin(normalized)
        _, name_confident = self._extract_full_name(lines)
        return (
            (10 if iin_valid else 0)
            + len(DATE_RE.findall(normalized))
            + (5 if name_confident else 0)
            + sum(label in normalized.casefold() for label in NAME_LABELS)
        )

    def _extract_iin(
        self,
        text: str,
        ocr_candidates: Optional[list[tuple[str, int]]] = None,
    ) -> tuple[Optional[str], bool, Optional[bool]]:
        candidates: dict[str, tuple[int, bool, bool, bool]] = {}
        candidate_pattern = re.compile(
            r"(?<![A-ZА-ЯЁӘҒҚҢӨҰҮҺІ])([0-9OQОӨIІLl|ZЗSВ](?:[\s\-.:|]?[0-9OQОӨIІLl|ZЗSВ]){11})(?![A-ZА-ЯЁӘҒҚҢӨҰҮҺІ])",
            re.IGNORECASE,
        )
        lines = text.splitlines()
        for index, line in enumerate(lines):
            label = re.search(r"(?:иин|жсн|iin|identification\s*(?:number|no\.?))", line, re.IGNORECASE)
            search_text = line
            if label:
                search_text = line[label.end():] + " " + (lines[index + 1] if index + 1 < len(lines) else "")
            for match in candidate_pattern.finditer(search_text):
                digits = re.sub(r"\D", "", match.group(1).translate(IIN_OCR_CHARS))
                if len(digits) != 12:
                    continue
                score = 5 if label else 0
                valid_date = self._iin_has_valid_birth_date(digits)
                valid_checksum = self._iin_checksum_valid(digits)
                score += 3 if valid_date else 0
                score += 10 if valid_checksum else 0
                previous = candidates.get(digits)
                evidence = (score, bool(label), valid_checksum, valid_date)
                if previous is None or evidence[0] > previous[0]:
                    candidates[digits] = evidence

            if label is None:
                continue
            trailing_match = re.search(r"(?:иин|жсн|iin|identification\s*(?:number|no\.?))\s*[:\-]?\s*([0-9OQОӨIІLl|ZЗSВ\s\-.:|]{12,24})", line, re.IGNORECASE)
            if trailing_match:
                digits = re.sub(r"\D", "", trailing_match.group(1).translate(IIN_OCR_CHARS))
                if len(digits) == 12:
                    valid_date = self._iin_has_valid_birth_date(digits)
                    valid_checksum = self._iin_checksum_valid(digits)
                    score = 12 + (3 if valid_date else 0) + (10 if valid_checksum else 0)
                    previous = candidates.get(digits)
                    evidence = (score, True, valid_checksum, valid_date)
                    if previous is None or evidence[0] > previous[0]:
                        candidates[digits] = evidence
        for digits, confidence in ocr_candidates or []:
            if len(digits) != 12 or not digits.isdigit():
                continue
            valid_date = self._iin_has_valid_birth_date(digits)
            valid_checksum = self._iin_checksum_valid(digits)
            score = 8 + min(confidence // 10, 10) + (3 if valid_date else 0) + (10 if valid_checksum else 0)
            previous = candidates.get(digits)
            evidence = (score, confidence >= 60, valid_checksum, valid_date)
            if previous is None or evidence[0] > previous[0]:
                candidates[digits] = evidence
        if not candidates:
            return None, False, None
        value, evidence = max(candidates.items(), key=lambda item: item[1][0])
        _, trusted_source, valid_checksum, valid_date = evidence
        recognized = valid_date and (valid_checksum or trusted_source)
        return value, recognized, valid_checksum

    def _iin_has_valid_birth_date(self, value: str) -> bool:
        century_code = int(value[6])
        century = {1: 1800, 2: 1800, 3: 1900, 4: 1900, 5: 2000, 6: 2000}.get(century_code)
        if century is None:
            return False
        year = century + int(value[0:2])
        try:
            __import__("datetime").date(year, int(value[2:4]), int(value[4:6]))
            return True
        except ValueError:
            return False

    def _iin_checksum_valid(self, value: str) -> bool:
        if len(value) != 12 or not value.isdigit():
            return False
        first_weights = (1, 2) * 5 + (1,)
        checksum = sum(int(digit) * weight for digit, weight in zip(value[:11], first_weights)) % 11
        if checksum == 10:
            weights = (3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2)
            checksum = sum(int(digit) * weight for digit, weight in zip(value[:11], weights)) % 11
        return checksum != 10 and checksum == int(value[11])

    def _extract_full_name(self, lines: list[str]) -> tuple[Optional[str], bool]:
        values: dict[str, str] = {}
        label_patterns = {
            "surname": SURNAME_LABEL,
            "given": GIVEN_NAME_LABEL,
            "patronymic": PATRONYMIC_LABEL,
        }
        for index, line in enumerate(lines):
            if re.search(r"(?:^|\s)(?:фио|full\s*name|name)(?:\s|:|$)", line, re.IGNORECASE):
                for next_index in range(index + 1, min(index + 4, len(lines))):
                    candidate = self._clean_name_part(lines[next_index])
                    if candidate:
                        return candidate, True
                remainder = line.split(" ", 1)[-1] if " " in line else ""
                candidate = self._clean_name_part(remainder)
                if candidate:
                    return candidate, True

            for kind, pattern in label_patterns.items():
                match = pattern.search(line)
                if not match:
                    continue
                remainder = line[match.end():]
                remainder = NAME_LABEL_RE.sub(" ", remainder)
                remainder = re.sub(r"^[\s:/|,;.-]+", "", remainder)
                candidate = self._clean_name_part(remainder)
                if not candidate and index + 1 < len(lines) and not NAME_LABEL_RE.search(lines[index + 1]):
                    candidate = self._clean_name_part(lines[index + 1])
                if candidate:
                    values.setdefault(kind, candidate)

        if "surname" in values and "given" in values:
            full_name = " ".join(values[key] for key in ("surname", "given", "patronymic") if values.get(key))
            return full_name, True

        fallback = self._guess_name(lines)
        return fallback, bool(fallback and len(fallback.split()) >= 2)

    def _clean_name_part(self, value: str) -> Optional[str]:
        value = NAME_LABEL_RE.sub(" ", value)
        value = re.sub(r"[^A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі'’\- ]", " ", value)
        words = [word.strip("-'’") for word in value.split()]
        words = [word for word in words if len(word) >= 2]
        if not words or any(word.casefold() in SERVICE_WORDS for word in words):
            return None
        if len(words) > 3 or sum(char.isalpha() for word in words for char in word) < 2:
            return None
        return " ".join(words)

    def _line_has_label(self, line: str, labels: tuple[str, ...]) -> bool:
        line_norm = " ".join(line.split()).casefold()
        return any(label.casefold() in line_norm for label in labels)

    def _extract_labeled_date(self, lines: list[str], labels: tuple[str, ...], take_last: bool = False) -> Optional[str]:
        for index, line in enumerate(lines):
            if self._line_has_label(line, labels):
                matches = DATE_RE.findall(line)
                if matches:
                    return matches[-1] if take_last else matches[0]
                if index + 1 < len(lines):
                    next_matches = DATE_RE.findall(lines[index + 1])
                    if next_matches:
                        return next_matches[-1] if take_last else next_matches[0]
        return None

    def _guess_name(self, lines: list[str]) -> Optional[str]:
        candidates: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            cleaned_line = re.sub(r"[|_=]+", " ", line).strip()
            original_lowered = cleaned_line.casefold()
            if any(word in original_lowered for word in SERVICE_WORDS):
                continue
            if NAME_LABEL_RE.search(cleaned_line):
                cleaned_line = NAME_LABEL_RE.sub(" ", cleaned_line)
            lowered = cleaned_line.casefold()
            words = [re.sub(r"[^A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі'’\-]", "", w) for w in re.split(r"\s+", cleaned_line)]
            words = [word for word in words if word]
            if not 2 <= len(words) <= 4 or not all(len(word) >= 2 for word in words):
                continue
            if sum(char.isalpha() for word in words for char in word) < 6:
                continue
            score = 1
            if any(label in lowered for label in NAME_LABELS):
                score += 3
            if index and any(label in lines[index - 1].casefold() for label in NAME_LABELS):
                score += 2
            if all(word.isupper() for word in words):
                score += 1
            candidates.append((score, " ".join(words)))
        if candidates:
            return max(candidates, key=lambda item: item[0])[1]
        return None


class OCRService:
    provider: OcrProvider = TesseractOcrProvider()

    @classmethod
    def process_document(cls, file_bytes: bytes, mime: str = "", filename: str = "") -> dict:
        return cls.provider.process(file_bytes, mime, filename)

    @classmethod
    def status(cls) -> tuple[bool, str]:
        return TesseractOcrProvider()._configure()
