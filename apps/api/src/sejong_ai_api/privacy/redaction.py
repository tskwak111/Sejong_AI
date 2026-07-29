from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Final


class PiiCategory(str, Enum):  # noqa: UP042 - approved wire-independent value contract
    NAME = "NAME"
    RESIDENT_REGISTRATION_NUMBER = "RESIDENT_REGISTRATION_NUMBER"
    PASSPORT_OR_LICENSE = "PASSPORT_OR_LICENSE"
    PHONE_NUMBER = "PHONE_NUMBER"
    EMAIL = "EMAIL"
    DETAILED_ADDRESS = "DETAILED_ADDRESS"
    FINANCIAL_ACCOUNT = "FINANCIAL_ACCOUNT"
    PAYMENT_CARD = "PAYMENT_CARD"
    AUTH_SECRET = "AUTH_SECRET"
    VEHICLE_PLATE = "VEHICLE_PLATE"
    CASE_REFERENCE = "CASE_REFERENCE"
    SENSITIVE_HEALTH_WELFARE = "SENSITIVE_HEALTH_WELFARE"
    PRECISE_LOCATION = "PRECISE_LOCATION"


class UnresolvedReason(str, Enum):  # noqa: UP042 - approved value contract
    INPUT_INVALID = "INPUT_INVALID"
    UNSAFE_UNICODE = "UNSAFE_UNICODE"
    AMBIGUOUS_PERSON_NAME = "AMBIGUOUS_PERSON_NAME"
    AMBIGUOUS_DETAILED_ADDRESS = "AMBIGUOUS_DETAILED_ADDRESS"
    RESIDUAL_HIGH_RISK_PATTERN = "RESIDUAL_HIGH_RISK_PATTERN"


def _replacement(category: PiiCategory) -> str:
    return {
        PiiCategory.RESIDENT_REGISTRATION_NUMBER: "[주민등록번호]",
        PiiCategory.PAYMENT_CARD: "[카드번호]",
        PiiCategory.FINANCIAL_ACCOUNT: "[계좌번호]",
        PiiCategory.AUTH_SECRET: "[인증정보]",
        PiiCategory.PASSPORT_OR_LICENSE: "[여권·면허번호]",
        PiiCategory.PHONE_NUMBER: "[전화번호]",
        PiiCategory.EMAIL: "[이메일]",
        PiiCategory.PRECISE_LOCATION: "[정밀위치]",
        PiiCategory.VEHICLE_PLATE: "[차량번호]",
        PiiCategory.CASE_REFERENCE: "[접수번호]",
        PiiCategory.DETAILED_ADDRESS: "[상세주소]",
        PiiCategory.NAME: "[이름]",
        PiiCategory.SENSITIVE_HEALTH_WELFARE: "[건강·복지정보]",
    }[category]


@dataclass(frozen=True, slots=True)
class RedactionFinding:
    category: PiiCategory
    start: int
    end: int
    replacement: str

    def __post_init__(self) -> None:
        if (
            type(self.category) is not PiiCategory
            or type(self.start) is not int
            or type(self.end) is not int
            or self.start < 0
            or self.end <= self.start
            or self.replacement != _replacement(self.category)
        ):
            raise ValueError("REDACTION_FINDING_INVALID")


@dataclass(frozen=True, slots=True)
class RedactionResult:
    masked_text: str | None
    findings: tuple[RedactionFinding, ...]
    safe_for_failure_storage: bool
    safe_for_synthetic_provider: bool
    unresolved_reason: UnresolvedReason | None

    def __post_init__(self) -> None:
        findings_are_valid = type(self.findings) is tuple and all(
            type(item) is RedactionFinding for item in self.findings
        )
        if not findings_are_valid:
            raise ValueError("REDACTION_RESULT_INVALID")
        if self.masked_text is None:
            if (
                self.safe_for_failure_storage is not False
                or self.safe_for_synthetic_provider is not False
                or type(self.unresolved_reason) is not UnresolvedReason
            ):
                raise ValueError("REDACTION_RESULT_INVALID")
            return
        if (
            type(self.masked_text) is not str
            or not self.masked_text
            or self.safe_for_failure_storage is not True
            or self.safe_for_synthetic_provider is not True
            or self.unresolved_reason is not None
        ):
            raise ValueError("REDACTION_RESULT_INVALID")


_MAX_QUESTION_LENGTH: Final = 1000
_REMOVED_FORMAT_CHARACTERS: Final = (
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",
)
_UNSAFE_BIDI_CLASSES: Final = frozenset(
    {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
)
_KOREAN_SURNAME_INITIALS: Final = (
    "김이박최정강조윤장임한오서신권황안송전홍유고문양손배백허남심노하곽성차주우구"
    "민류나진지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모"
    "탁국어은편용예봉사부가복태목형계피두감동온빈"
)
_COMMON_KOREAN_SURNAME_INITIALS: Final = (
    "김이박최정강조윤장임한오서신권황안송전홍유고문양손배백허남심노곽성차주우구민류나진"
)
_KOREAN_COMPOUND_SURNAMES: Final = "독고|남궁|황보|제갈|사공|선우|서문|동방"
_KOREAN_PERSON_NAME_PATTERN: Final = (
    rf"(?:(?:{_KOREAN_COMPOUND_SURNAMES})[가-힣]{{1,2}}|"
    rf"[{_KOREAN_SURNAME_INITIALS}][가-힣]{{1,3}})"
)
_KOREAN_CONTEXTUAL_NAME_PATTERN: Final = (
    rf"(?:(?:{_KOREAN_COMPOUND_SURNAMES})[가-힣]{{1,2}}|"
    rf"[{_KOREAN_SURNAME_INITIALS}][가-힣]{{2}})"
)
_AUTH_LABEL_PATTERN: Final = (
    r"(?:비밀번호|비번|패스워드|인증\s*번호|인증\s*코드|인증\s*문자|"
    r"로그인\s*암호|문자\s*인증\s*값|일회용\s*번호|"
    r"접속\s*암호|문자\s*확인\s*코드|본인\s*인증\s*값|"
    r"(?:로그인|접속|일회용)\s*(?:암호|비밀\s*키)|"
    r"(?:보안|인증|접속)\s*(?:토큰|비밀\s*키)|"
    r"(?:본인|문자)\s*(?:인증|확인)(?:용)?\s*(?:번호|코드|값|숫자)|"
    r"본인\s*확인\s*코드|보안\s*코드|"
    r"본인\s*인증용\s*확인\s*번호|(?:문자로\s+받은\s+)?6자리\s+코드|"
    r"확인\s*번호|인증\s*키|보안\s*키|"
    r"(?<![A-Z0-9])(?>OTP(?:\s*번호)?)(?=$|[\s:：,.!?]|[은는이가을를](?=[\s:：]))|"
    r"(?<![A-Z0-9])(?>PIN(?:\s*번호)?)(?=$|[\s:：,.!?]|[은는이가을를](?=[\s:：])))"
)
_PASSPORT_LICENSE_LABEL_PATTERN: Final = (
    r"(?:여권\s*번호|여권|운전\s*면허(?:증)?(?:\s*번호)?|면허(?:증)?\s*번호)"
)
_CASE_LABEL_PATTERN: Final = (
    r"(?:접수(?:\s*번호|\s*코드|\s*ID)|민원\s*번호|"
    r"신청\s*번호|처리\s*번호|배출(?:\s*신고)?\s*번호)"
)
_VEHICLE_PLATE_SYLLABLES: Final = (
    "가나다라마거너더러머버서어저고노도로모보소오조구누두루무부수우주아바사자배하허호"
)


def _closed(
    reason: UnresolvedReason,
    findings: tuple[RedactionFinding, ...] = (),
) -> RedactionResult:
    return RedactionResult(None, findings, False, False, reason)


def _normalize(raw_question: object) -> tuple[str | None, UnresolvedReason | None]:
    if type(raw_question) is not str:
        return None, UnresolvedReason.INPUT_INVALID
    if not raw_question or len(raw_question) > _MAX_QUESTION_LENGTH or not raw_question.strip():
        return None, UnresolvedReason.INPUT_INVALID
    normalized = unicodedata.normalize(
        "NFKC",
        raw_question.replace("\r\n", "\n").replace("\r", "\n"),
    )
    for character in _REMOVED_FORMAT_CHARACTERS:
        normalized = normalized.replace(character, "")
    if not normalized or len(normalized) > _MAX_QUESTION_LENGTH or not normalized.strip():
        return None, UnresolvedReason.INPUT_INVALID
    for character in normalized:
        category = unicodedata.category(character)
        if category == "Cs":
            return None, UnresolvedReason.UNSAFE_UNICODE
        if category == "Cc" and character not in {"\t", "\n"}:
            return None, UnresolvedReason.UNSAFE_UNICODE
        if category == "Cf" or unicodedata.bidirectional(character) in _UNSAFE_BIDI_CLASSES:
            return None, UnresolvedReason.UNSAFE_UNICODE
    return normalized, None


@dataclass(frozen=True, slots=True)
class _Rule:
    category: PiiCategory
    pattern: re.Pattern[str]


_CATEGORY_PRIORITY: Final = (
    PiiCategory.RESIDENT_REGISTRATION_NUMBER,
    PiiCategory.PAYMENT_CARD,
    PiiCategory.FINANCIAL_ACCOUNT,
    PiiCategory.AUTH_SECRET,
    PiiCategory.PASSPORT_OR_LICENSE,
    PiiCategory.PHONE_NUMBER,
    PiiCategory.EMAIL,
    PiiCategory.PRECISE_LOCATION,
    PiiCategory.VEHICLE_PLATE,
    PiiCategory.CASE_REFERENCE,
    PiiCategory.DETAILED_ADDRESS,
    PiiCategory.NAME,
    PiiCategory.SENSITIVE_HEALTH_WELFARE,
)
_RULES: Final = (
    _Rule(
        PiiCategory.RESIDENT_REGISTRATION_NUMBER,
        re.compile(r"(?<!\d)(?P<value>\d{6}\s*[- ]?\s*[1-8]\d{6})(?!\d)"),
    ),
    _Rule(
        PiiCategory.PAYMENT_CARD,
        re.compile(
            r"(?<!\d)(?P<value>(?:\d{4}(?:[- .]?\d{4}){3}[- .]?\d{3}|"
            r"\d{4}(?:[- .]?\d{4}){3}[- .]?\d{2}|"
            r"\d{4}(?:[- .]?\d{4}){3}[- .]?\d|"
            r"\d{4}(?:[- .]?\d{4}){3}|"
            r"\d{4}[- .]?\d{6}[- .]?\d{5}|"
            r"\d{4}(?:[- .]?\d{4}){2}[- .]?\d{2}|"
            r"\d{4}(?:[- .]?\d{4}){2}[- .]?\d))(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.FINANCIAL_ACCOUNT,
        re.compile(
            r"(?:계좌(?:번호)?|입금계좌|통장(?:번호)?)(?:은|는|이|가)?\s*[:：]?\s*"
            r"(?P<value>\d{2,6}(?:[- ]\d{2,6}){1,4})"
        ),
    ),
    _Rule(
        PiiCategory.FINANCIAL_ACCOUNT,
        re.compile(
            r"(?<!\d)(?P<value>(?:\d{3}-\d{6}-\d{2}-\d{3}|"
            r"\d{3}-\d{3}-\d{6}|\d{6}-\d{2}-\d{6}|"
            r"\d{3}-\d{6}-\d{5}|(?!0(?:30|50[2-8]))\d{4}-\d{4}-\d{4}|"
            r"\d{3}-\d{2}-\d{6}|\d{4}-\d{2}-\d{6}|"
            r"\d{3}-\d{6}-\d{3}))(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.AUTH_SECRET,
        re.compile(
            rf"{_AUTH_LABEL_PATTERN}(?:은|는|이|가|을|를)?"
            r"(?:\s*[:：]\s*|\s+)(?!\s*\[)"
            r"(?P<value>[A-Z0-9!#$%&()*+,\-./:;<=>?@\^_`{|}~ ]{3,63}"
            r"[A-Z0-9!#$%&()*+\-/:;<=>?@\^_`{|}~])"
            r"(?=$|[\s,.!?]|을\s|를\s|입니다|이에요|예요|이고|라고)",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.AUTH_SECRET,
        re.compile(
            rf"{_AUTH_LABEL_PATTERN}(?:은|는)?"
            r"(?:\s*[:：]\s*|\s+)(?!\s*\[)"
            r"(?P<value>(?:[가-힣]{2,4}|[가-힣](?:\s+[가-힣]){1,7}|실제\s+비밀))"
            r"(?=(?:입니다|이에요|예요|이고|라고)?(?:$|[,.!?]))",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PASSPORT_OR_LICENSE,
        re.compile(
            rf"{_PASSPORT_LICENSE_LABEL_PATTERN}\s*[:：]?\s*"
            r"(?P<value>(?:[A-Z]\d{8}|(?:[가-힣]{2,4}\s*)?"
            r"\d{2}(?:-\d{2})?-\d{6}-\d{2}))",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PASSPORT_OR_LICENSE,
        re.compile(
            r"(?<![A-Z0-9])(?P<value>[A-Z]{1,2}\s*\d{7,8}|"
            r"(?:(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|"
            r"충북|충남|전북|전남|경북|경남|제주)\s+)?"
            r"\d{2}-\d{2}-\d{6}-\d{2})"
            r"(?![A-Z0-9])",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PASSPORT_OR_LICENSE,
        re.compile(
            r"(?<![A-Z0-9])(?P<value>[A-Z0-9]{8,9})"
            r"(?=(?:은|는|이|가|로)?\s+(?:제\s+|영국\s+)?여권(?:\s*번호)?)",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(
            r"(?<![\d+])(?P<value>\+82[- .]?(?:\(0\)[- .]?)?"
            r"(?:1[016789]|70|2|[3-6][1-5])[- .]?\d{3,4}[- .]?\d{4})(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(
            r"(?<!\d)(?P<value>(?:01[016789]|070)(?:[- .]?\d{3,4})"
            r"[- .]?\d{4}(?:\s+내선(?:번호)?\s*\d{1,6})?)(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(
            r"(?<!\d)(?P<value>050[2-8](?:[- .]?\d{3,4})"
            r"[- .]?\d{4}(?:\s+내선(?:번호)?\s*\d{1,6})?)(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(r"(?<!\d)(?P<value>030[- .]?\d{5}[- .]?\d{4})(?!\d)"),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(
            r"(?<!\d)(?P<value>0(?:2|[3-6][1-5])[- .]?\d{3,4}"
            r"[- .]?\d{4}(?:\s+내선(?:번호)?\s*\d{1,6})?)(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(r"(?<!\d)(?P<value>1[568]\d{2}[- .]?\d{4})(?!\d)"),
    ),
    _Rule(
        PiiCategory.PHONE_NUMBER,
        re.compile(
            r"(?:대표전화|대표번호|콜센터)(?:은|는|이|가)?\s*[:：]?\s*"
            r"(?P<value>1\d{2,3})(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.EMAIL,
        re.compile(
            r"(?<![\w.+-])(?P<value>[A-Z0-9._%+\-]+@[A-Z0-9.\-]+"
            r"\.[A-Z]{2,})(?![\w.-])",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?:(?<![\d.])(?P<value>-?\d{1,2}\.\d+\s*[,;]\s*"
            r"-?\d{1,3}\.\d+)(?![\d.])|"
            r"(?:좌표\s*[:：]?\s*(?P<value_coords>-?\d{1,2}\.\d+\s+"
            r"-?\d{1,3}\.\d+))(?![\d.])|"
            r"(?:위도\s*[:：]?\s*(?P<value_lat>-?\d{1,2}(?:\.\d+)?)\s*,?\s*"
            r"경도\s*[:：]?\s*(?P<value_lng>-?\d{1,3}(?:\.\d+)?))|"
            r"(?P<value_compass>-?\d{1,2}(?:\.\d+)?\s*°\s*[NS]\s+"
            r"-?\d{1,3}(?:\.\d+)?\s*°\s*[EW]))",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"경도\s*[:：]?\s*(?P<value_coords>-?\d{1,3}(?:\.\d+)?\s*,?\s*"
            r"위도\s*[:：]?\s*-?\d{1,2}(?:\.\d+)?)"
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"북위\s*(?P<value_coords>\d{1,2}\s*도\s*\d{1,2}\s*분\s*,?\s*"
            r"동경\s*\d{1,3}\s*도\s*\d{1,2}\s*분)"
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?P<value>(?:북위\s*\d{1,2}(?:\.\d+)?\s*,\s*"
            r"동경\s*\d{1,3}(?:\.\d+)?|"
            r"동경\s*\d{1,3}\s*도\s*\d{1,2}\s*분(?:\s*\d{1,2}\s*초)?\s*,\s*"
            r"북위\s*\d{1,2}\s*도\s*\d{1,2}\s*분(?:\s*\d{1,2}\s*초)?|"
            r"북위\s*\d{1,2}\s*도\s*\d{1,2}\s*분\s*\d{1,2}\s*초\s*,\s*"
            r"동경\s*\d{1,3}\s*도\s*\d{1,2}\s*분\s*\d{1,2}\s*초))"
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?P<value>(?:(?:북위|N)\s*\d{1,2}(?:\.\d+)?\s*도?\s*[,/]\s*"
            r"(?:동경|경도|E)\s*\d{1,3}(?:\.\d+)?\s*도?|"
            r"위도\s*\d{1,2}(?:\.\d+)?\s*/\s*경도\s*\d{1,3}(?:\.\d+)?|"
            r"(?:동경|E)\s*\d{1,3}(?:\.\d+)?\s*도?\s*[,/]\s*"
            r"(?:북위|N)\s*\d{1,2}(?:\.\d+)?\s*도?))",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?<![\d.])(?P<value>-?\d{1,2}\.\d+\s+-?\d{1,3}\.\d+)"
            r"(?=에\s+(?:있습니다|있어요|있다))(?![\d.])"
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?P<value>(?:[NS]\s*-?\d{1,2}\.\d+\s+[EW]\s*-?\d{1,3}\.\d+)|"
            r"(?:-?\d{1,2}°\d{1,2}'\d{1,2}(?:\.\d+)?\"[NS]\s+"
            r"-?\d{1,3}°\d{1,2}'\d{1,2}(?:\.\d+)?\"[EW]))",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"(?P<value>-?\d{1,2}°\d{1,2}'\d{1,2}(?:\.\d+)?\"[NS]\s*,\s*"
            r"-?\d{1,3}°\d{1,2}'\d{1,2}(?:\.\d+)?\"[EW])",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.PRECISE_LOCATION,
        re.compile(
            r"위도\s*[:：]?\s*(?P<value>\d{1,2}\s*도\s*\d{1,2}\s*분\s*"
            r"경도\s*[:：]?\s*\d{1,3}\s*도\s*\d{1,2}\s*분)"
        ),
    ),
    _Rule(
        PiiCategory.VEHICLE_PLATE,
        re.compile(
            rf"(?<!\d)(?P<value>\d\s*\d(?:\s*\d)?\s*[-· ]?\s*[{_VEHICLE_PLATE_SYLLABLES}]"
            r"\s*[-· ]?\s*\d\s*\d\s*\d\s*\d)(?!\d)"
        ),
    ),
    _Rule(
        PiiCategory.VEHICLE_PLATE,
        re.compile(
            rf"(?P<value>(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|"
            rf"충북|충남|전북|전남|경북|경남|제주)\s+[가-힣]{{1,4}}\s+"
            rf"[{_VEHICLE_PLATE_SYLLABLES}]\s*[-· ]?\s*\d{{4}})"
        ),
    ),
    _Rule(
        PiiCategory.VEHICLE_PLATE,
        re.compile(r"(?P<value>(?:외교|준외|영사|국기|협정)\s*\d{3}[- ]\d{3})(?!\d)"),
    ),
    _Rule(
        PiiCategory.CASE_REFERENCE,
        re.compile(
            rf"{_CASE_LABEL_PATTERN}(?:은|는|이|가)?\s*[:：]?\s*"
            r"(?P<value>(?:[A-Z]+-)?\d{4}-\d{6}|\d{4}-\d{2}-\d{6}|"
            r"[A-Z]+-\d{6}|\d{6}-\d{7})",
            re.IGNORECASE,
        ),
    ),
    _Rule(
        PiiCategory.CASE_REFERENCE,
        re.compile(r"(?<![A-Z0-9])(?P<value>SJ-\d{4}-\d{6})(?![A-Z0-9])", re.IGNORECASE),
    ),
    _Rule(
        PiiCategory.DETAILED_ADDRESS,
        re.compile(
            r"(?:(?:주소(?:는)?|사는\s*곳|거주지|상세주소)\s*[:：]?\s*)?"
            r"(?P<value>(?:(?:세종특별자치시|세종시)\s*)?(?:[가-힣]+(?:읍|면|동)\s+)?"
            r"[가-힣0-9]+(?:대로|로|길)\s*\d+(?:\s*-\s*\d+)?"
            r"(?:(?:\s*,?\s*)\d+동\s*\d+호|(?:\s*,?\s*)\d+층)?)"
        ),
    ),
    _Rule(
        PiiCategory.DETAILED_ADDRESS,
        re.compile(
            r"(?P<value>(?:(?:세종특별자치시|세종시)\s+)?"
            r"(?:[가-힣]+(?:읍|면)\s+)?[가-힣]+리\s+(?:산\s*)?"
            r"\d+(?:\s*-\s*\d+)?)"
        ),
    ),
    _Rule(
        PiiCategory.DETAILED_ADDRESS,
        re.compile(
            r"(?P<value>[가-힣]+동\s+[가-힣0-9]{2,24}(?:빌|타워)\s+\d+\s*(?:호|층)|"
            r"[가-힣]+동\s+[가-힣0-9]{2,24}(?:아파트|주택|오피스텔|빌라)\s+"
            r"[A-Z0-9가-힣]+동\s+\d+호)"
        ),
    ),
    _Rule(
        PiiCategory.DETAILED_ADDRESS,
        re.compile(
            r"(?P<value>[가-힣]+동\s+(?!\d+\s*번지)[가-힣0-9]{2,24}\s+"
            r"(?:(?:[A-Z0-9가-힣]+동\s+)?\d+\s*(?:호|층)|"
            r"[A-Z]\d+\s*호|지하\s+(?:[A-Z]?\d+\s*호|\d+\s*층)))"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            r"(?:제\s+)?(?:본명|실명|등록명|호적명)(?:은|는|이|가)?"
            r"(?:\s*[:：]\s*|\s+)"
            r"(?P<value>[가-힣]{2,8})"
            r"(?=\(가명\)|\(본인\)|입니다|이에요|예요|이고|라고|[,.!?]|$)"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            rf"(?:제\s+)?성함(?:은|는|이|가)?(?:\s*[:：]\s*|\s+)"
            rf"(?P<value>{_KOREAN_PERSON_NAME_PATTERN})"
            r"(?=\(가명\)|\(본인\)|입니다|이에요|예요|이고|라고|[,.!?]|$)"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            r"(?<![가-힣])(?P<value>독고[가-힣]{1,2})"
            r"(?=\s*(?:입니다|이에요|예요|이고|라고)(?:[\s,.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            rf"(?:전입신고|주민등록|주민센터|지방세|가족관계|대형폐기물|증명서|"
            rf"자동차세|민원)\s+(?P<value>{_KOREAN_CONTEXTUAL_NAME_PATTERN})"
            r"(?=\s+(?:후|관련|문의|신청|처리))"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            r"(?:민원인|신청인|보호자)"
            r"(?:\s*[:：]\s*|\s+)(?!이름|성명|어디|어떻게)"
            rf"(?P<value>[{_KOREAN_SURNAME_INITIALS}](?:\s*[가-힣]){{1,3}})"
            r"(?=\(가명\)|\(본인\)|입니다|이에요|예요|이고|라고|[,.!?]|$)"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            r"(?:신청인\s+(?:이름|성명)|이름|성명|신청인(?!\s+(?:이름|성명)))"
            r"(?:은|는|이|가|을|를)?(?:\s*[:：]\s*|\s+)"
            r"(?!어디|어떻게|언제|왜|무엇|뭐|몇|꼭|나오나요|적어야|"
            r"없이|없어도|필요|표시|가려|변경\s+방법|확인\s+방법|"
            r"잘못|틀리|틀렸|오류|누락|아직|모르|안\s+|한글|달라|다르게|"
            r"고치|오자|선택|스티커)"
            r"(?P<value>[가-힣](?:\s*[가-힣]){1,3})"
            r"(?=\(가명\)|\(본인\)|입니다|이에요|예요|이고|"
            r"이라고|라고(?:\s+(?:합니다|해요))?|[,.!?]|$)"
        ),
    ),
    _Rule(
        PiiCategory.NAME,
        re.compile(
            r"저는\s*(?P<value>[가-힣]{2,4})"
            r"(?=\s*(?:입니다|이에요|예요|이고|라고(?:\s+합니다)?))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:고혈압|당뇨병?|암|천식|치매|우울증|희귀병|"
            r"신장병|크론병|뇌전증|조현병|시각장애|청각장애))"
            r"(?=(?:이|가)?\s*(?:있습니다|있어요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>[가-힣]{1,8}(?:병|증|장애|경화|부전))"
            r"(?=(?:이|가)?\s*(?:있습니다|있어요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:파킨슨병|루푸스))"
            r"(?=(?:이|가)?\s*(?:있습니다|있어요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>임신)(?=했어요(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>투석\s+중)(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:의료급여\s+대상자|생계급여\s+수급자))"
            r"(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:암\s*\d+\s*기|장애\s*\d+\s*급|중증장애인))"
            r"(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>기초생활수급)(?=을\s+받고\s+(?:있습니다|있어요)(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>임신\s+중)(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>임신\s+\d{1,2}\s*주)(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:생계급여|의료급여|주거급여|교육급여)\s+수급자)"
            r"(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(r"(?P<value>한부모\s*가정)(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?:[가-힣]{2,12}\s+)?(?:수급자|지원\s*대상자))"
            r"(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"진단(?:은|는|이|가)\s*[:：]?\s*"
            r"(?!어디|어떻게|언제|왜|무엇|뭐|확인)"
            r"(?P<value>[가-힣]{1,20})(?=\s*(?:입니다|이에요|예요)(?:[.!?]|$))"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?P<value>(?<![가-힣])(?!(?:저는|제가|본인은|민원인은)\s)"
            r"[가-힣]{1,12}(?:\s+[가-힣0-9]{1,8}){0,3}\s+"
            r"(?:진단|치료(?:\s+중)?|환자)|장애등급\s*\d+급|"
            r"기초생활수급자|차상위\s*계층|한부모\s*가족)"
        ),
    ),
    _Rule(
        PiiCategory.SENSITIVE_HEALTH_WELFARE,
        re.compile(
            r"(?:진단명|복지대상)(?:은|는|이|가|을|를)?"
            r"(?:\s*[:：]\s*|\s+)(?!\s*\[)"
            r"(?!어디|어떻게|언제|왜|무엇|뭐|변경\s+방법|확인\s+방법)"
            r"(?P<value>[^\n,.!?]{1,100}?)"
            r"(?=$|[,.!?]|입니다|이에요|예요|이고|라고)"
        ),
    ),
)

_AMBIGUOUS_NAME: Final = re.compile(
    r"(?:(?<![가-힣])(?P<value>[가-힣]{2,4})\s*(?:씨|님)"
    r"(?=이라고|라고|\s*입니다|\s*이에요|\s*예요|[\s,.!?]|$)|"
    r"(?:민원인|신청인)(?:은|는)\s*"
    r"(?P<labeled_value>(?!어디|어떻게|언제|왜|무엇|뭐)[가-힣]{2,4})"
    r"(?=\s*입니다|\s*이에요|\s*예요|[\s,.!?]|$)|"
    rf"(?<![가-힣])(?P<standalone_value>[{_KOREAN_SURNAME_INITIALS}][가-힣]{{1,3}})"
    r"(?=\s*(?:입니다|이에요|예요|라고\s+(?:합니다|해요))(?:[\s,.!?]|$))|"
    r"(?<![가-힣])(?P<spaced_value>[가-힣]\s+[가-힣](?:\s*[가-힣]){0,2})"
    r"(?=\s*(?:입니다|이에요|예요)(?:[\s,.!?]|$)))"
)
_SAFE_STANDALONE_NAME_TERMS: Final = frozenset(
    {
        "전입신고",
        "주민등록",
        "주민번호",
        "주민센터",
        "지방세",
        "가족관계",
        "여권",
        "계좌",
        "주소",
        "위치",
        "전화번호",
        "복지대상",
        "진단명",
        "진단은",
        "인증번호",
        "민원번호",
        "차량번호",
        "한솔동",
        "도담동",
        "아름동",
        "조치원읍",
        "이메일",
        "이름",
        "이름은",
        "이름을",
        "이에요",
        "입니다",
        "위도",
        "경도",
        "신청서",
        "민원인",
        "신청인",
        "담당자",
        "가명",
        "설명이",
    }
)
_SAFE_ADMIN_LOCALITIES: Final = frozenset(
    {
        "세종시",
        "조치원읍",
        "연기면",
        "연동면",
        "부강면",
        "금남면",
        "장군면",
        "연서면",
        "전의면",
        "전동면",
        "소정면",
        "한솔동",
        "새롬동",
        "나성동",
        "도담동",
        "어진동",
        "아름동",
        "종촌동",
        "고운동",
        "보람동",
        "대평동",
        "소담동",
        "반곡동",
        "다정동",
        "해밀동",
        "집현동",
    }
)
_AMBIGUOUS_ADDRESS: Final = re.compile(
    r"(?P<value>(?:[가-힣0-9]+\s*(?:아파트|빌라|오피스텔|단지|주공|타워)\s*\d+\s*동\s*"
    r"(?:[-,]\s*)?\d+\s*호|"
    r"\d+\s*동\s*\d+\s*호|"
    r"(?:[가-힣]+(?:읍|면|동)\s*)\d+\s*-\s*\d+(?:\s*\d+\s*호)?|"
    r"(?:[가-힣]+(?:읍|면|동)\s*)?\d+\s*(?:-\s*\d+\s*)?번지"
    r"(?:\s*\d+\s*(?:동|호))*))"
)
_POSSIBLE_KOREAN_NAME: Final = re.compile(
    rf"(?P<value>[{_KOREAN_SURNAME_INITIALS}](?:\s*[가-힣]){{1,3}})"
)
_POSSIBLE_NAME_NEXT_TO_FIXED_TOKEN: Final = re.compile(
    rf"(?:(?<![가-힣])(?P<before>{_KOREAN_CONTEXTUAL_NAME_PATTERN})"
    r"[^A-Z0-9가-힣\[\]]+(?=\[)|"
    rf"(?:\])[^A-Z0-9가-힣\[\]]+"
    rf"(?P<after>{_KOREAN_CONTEXTUAL_NAME_PATTERN})"
    r"(?=$|[)\s,.!?]))"
)
_NAME_ADJACENT_ADMIN_TERM: Final = (
    r"(?:전입신고|주민등록|주민센터|지방세|가족관계|대형폐기물|증명서|자동차세|민원)"
)
_POSSIBLE_CONTEXTUAL_NAME: Final = re.compile(
    rf"(?:(?:문의자|신청자)\s+(?P<label_name>[{_KOREAN_SURNAME_INITIALS}][가-힣]{{1,3}})(?![가-힣])"
    rf"|(?<![가-힣])(?P<before_admin>[{_COMMON_KOREAN_SURNAME_INITIALS}][가-힣]{{2}})(?![가-힣])\s+"
    rf"{_NAME_ADJACENT_ADMIN_TERM}"
    rf"|{_NAME_ADJACENT_ADMIN_TERM}\s+"
    rf"(?P<after_admin>[{_COMMON_KOREAN_SURNAME_INITIALS}][가-힣]{{2}})"
    r"(?=$|[),.!?]|(?:입니다|이에요|예요|이라고|라고))"
    rf"|(?<=[?!.]\s)(?P<after_sentence>[{_KOREAN_SURNAME_INITIALS}][가-힣]{{1,3}})"
    r"(?=$|[)\s,.!?]))"
)
_POSSIBLE_CONTEXTUAL_NAME_AT_END: Final = re.compile(
    rf"(?<![가-힣])(?P<value>{_KOREAN_CONTEXTUAL_NAME_PATTERN})\s*$"
)
_POSSIBLE_CONTEXTUAL_NAME_ANYWHERE: Final = re.compile(
    rf"(?<![가-힣])(?P<value>{_KOREAN_CONTEXTUAL_NAME_PATTERN})(?![가-힣])"
)
_POSSIBLE_CONTEXTUAL_NAME_WITH_PARTICLE: Final = re.compile(
    rf"(?<![가-힣])(?P<value>{_KOREAN_CONTEXTUAL_NAME_PATTERN})(?:의|에게|한테)(?![가-힣])"
)
_SAFE_CONTEXTUAL_NAME_TERMS: Final = frozenset(
    {
        "가까운",
        "가족이",
        "가상로",
        "계좌는",
        "고지가",
        "고지서",
        "기한을",
        "기준을",
        "나와요",
        "납세자",
        "다르게",
        "도로명",
        "문자는",
        "문자로",
        "문서를",
        "방법은",
        "방법이",
        "방법을",
        "변경은",
        "사실을",
        "서류가",
        "사용합",
        "선택하면",
        "선택을",
        "성함",
        "성함은",
        "성명을",
        "성명은",
        "신고도",
        "신고를",
        "신고서",
        "신고자",
        "신고할",
        "신고용",
        "신청을",
        "신청인",
        "신청자",
        "신청할",
        "어디서",
        "어디에",
        "어때요",
        "어떻게",
        "안내가",
        "안내문",
        "안내를",
        "안내용",
        "연락을",
        "연락용",
        "연락해",
        "고지는",
        "오나요",
        "오자를",
        "온라인",
        "우편물",
        "위도와",
        "위치를",
        "이름과",
        "이름을",
        "이름이",
        "이메일",
        "이용할",
        "인가요",
        "인증키",
        "인증용",
        "전송이",
        "정보가",
        "주소가",
        "주소는",
        "주소도",
        "주소를",
        "장학금",
        "장애인",
        "지방세",
        "조회해",
        "주세요",
        "반드시",
        "전체를",
        "계좌를",
        "고치는",
        "나오면",
        "나중에",
        "남나요",
        "문자가",
        "정정할",
        "표기를",
        "필요해",
        "위치는",
        "확인해",
        "하나요",
        "하는데",
        "하려면",
        "한글로",
        "연락처",
        "성명이",
        "설명이",
        "테스트",
    }
)
_AMBIGUOUS_EXPLICIT_PII: Final = re.compile(
    r"(?<![A-Z0-9가-힣])(?:주민(?:\s*등록)?\s*번호|여권\s*번호|"
    r"(?:운전\s*)?면허(?:증)?\s*번호|운전\s*면허증|연락처|전화번호|휴대폰|이메일|메일|"
    r"주소|거주지|계좌번호|통장번호|카드\s*번호|비밀번호|비번|패스워드|"
    r"인증\s*번호|인증\s*코드|인증\s*문자|본인\s*확인\s*코드|"
    r"OTP(?:\s*번호)?|PIN(?:\s*번호)?|차량번호|번호판|"
    r"접수(?:\s*번호|\s*코드|\s*ID)|민원\s*번호|진단명|복지대상|GPS|위치)"
    r"(?:은|는|이|가|을|를)?(?![A-Z0-9가-힣])(?:\s*[:：]\s*|\s+)"
    r"(?!\[(?:이름|주민등록번호|여권·면허번호|전화번호|이메일|상세주소|계좌번호|"
    r"카드번호|인증정보|차량번호|접수번호|건강·복지정보|정밀위치)\]"
    r"(?=$|[\s,.!?]))"
    r"(?P<unclassified_value>(?=[^\n]*(?:@|\d|[A-Z]))[^\n]{2,})",
    re.IGNORECASE,
)
_HIGH_RISK_SPAN_PATTERNS: Final = (
    re.compile(r"(?<!\S)[^\s@]+@[^\s@,.!?]+(?=$|[\s,.!?])"),
    re.compile(
        r"(?<!\S)[A-Z0-9가-힣._%+\-]+\s*@\s*"
        r"[A-Z0-9가-힣\-]+(?:\.[A-Z0-9가-힣\-]+)+(?![\w.-])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![\w.+-])[A-Z0-9._%+\-]+@[A-Z0-9.\-]+"
        r"\.[A-Z]{2,}(?![\w.-])",
        re.IGNORECASE,
    ),
    re.compile(r"내선(?:번호)?\s*\d{1,6}"),
    re.compile(
        rf"(?<!\d)\d{{2,3}}(?:[^\w]|_)+[{_VEHICLE_PLATE_SYLLABLES}]"
        r"(?:[^\w]|_)+\d{4}(?!\d)"
    ),
)
_FIXED_TOKEN_BY_LABEL: Final = (
    ("주민번호", "[주민등록번호]"),
    ("주민 번호", "[주민등록번호]"),
    ("주민등록번호", "[주민등록번호]"),
    ("주민 등록 번호", "[주민등록번호]"),
    ("여권번호", "[여권·면허번호]"),
    ("여권 번호", "[여권·면허번호]"),
    ("여권", "[여권·면허번호]"),
    ("면허번호", "[여권·면허번호]"),
    ("면허 번호", "[여권·면허번호]"),
    ("면허증 번호", "[여권·면허번호]"),
    ("운전면허", "[여권·면허번호]"),
    ("운전면허증", "[여권·면허번호]"),
    ("운전 면허", "[여권·면허번호]"),
    ("운전 면허증", "[여권·면허번호]"),
    ("운전 면허 번호", "[여권·면허번호]"),
    ("운전 면허증 번호", "[여권·면허번호]"),
    ("연락처", "[전화번호]"),
    ("전화", "[전화번호]"),
    ("전화번호", "[전화번호]"),
    ("휴대폰", "[전화번호]"),
    ("이메일", "[이메일]"),
    ("메일", "[이메일]"),
    ("주소", "[상세주소]"),
    ("거주지", "[상세주소]"),
    ("계좌번호", "[계좌번호]"),
    ("계좌", "[계좌번호]"),
    ("카드번호", "[카드번호]"),
    ("카드 번호", "[카드번호]"),
    ("비밀번호", "[인증정보]"),
    ("비번", "[인증정보]"),
    ("패스워드", "[인증정보]"),
    ("로그인 암호", "[인증정보]"),
    ("접속 암호", "[인증정보]"),
    ("문자인증값", "[인증정보]"),
    ("문자 인증 값", "[인증정보]"),
    ("문자 확인 코드", "[인증정보]"),
    ("본인인증 값", "[인증정보]"),
    ("본인 인증 값", "[인증정보]"),
    ("일회용 번호", "[인증정보]"),
    ("인증번호", "[인증정보]"),
    ("인증 번호", "[인증정보]"),
    ("인증코드", "[인증정보]"),
    ("인증 코드", "[인증정보]"),
    ("인증문자", "[인증정보]"),
    ("인증 문자", "[인증정보]"),
    ("본인확인 코드", "[인증정보]"),
    ("본인 확인 코드", "[인증정보]"),
    ("보안코드", "[인증정보]"),
    ("보안 코드", "[인증정보]"),
    ("본인인증용 확인번호", "[인증정보]"),
    ("본인 인증용 확인 번호", "[인증정보]"),
    ("문자로 받은 6자리 코드", "[인증정보]"),
    ("6자리 코드", "[인증정보]"),
    ("확인번호", "[인증정보]"),
    ("확인 번호", "[인증정보]"),
    ("인증키", "[인증정보]"),
    ("인증 키", "[인증정보]"),
    ("보안키", "[인증정보]"),
    ("보안 키", "[인증정보]"),
    ("otp", "[인증정보]"),
    ("otp번호", "[인증정보]"),
    ("otp 번호", "[인증정보]"),
    ("pin", "[인증정보]"),
    ("pin번호", "[인증정보]"),
    ("pin 번호", "[인증정보]"),
    ("차량번호", "[차량번호]"),
    ("번호판", "[차량번호]"),
    ("접수번호", "[접수번호]"),
    ("접수 번호", "[접수번호]"),
    ("접수코드", "[접수번호]"),
    ("접수 코드", "[접수번호]"),
    ("접수 id", "[접수번호]"),
    ("민원번호", "[접수번호]"),
    ("민원 번호", "[접수번호]"),
    ("신청번호", "[접수번호]"),
    ("신청 번호", "[접수번호]"),
    ("처리번호", "[접수번호]"),
    ("처리 번호", "[접수번호]"),
    ("배출번호", "[접수번호]"),
    ("배출 번호", "[접수번호]"),
    ("배출신고번호", "[접수번호]"),
    ("배출 신고 번호", "[접수번호]"),
    ("진단명", "[건강·복지정보]"),
    ("복지대상", "[건강·복지정보]"),
    ("gps", "[정밀위치]"),
    ("위치", "[정밀위치]"),
    ("현재 위치", "[정밀위치]"),
    ("이름", "[이름]"),
    ("성명", "[이름]"),
    ("성함", "[이름]"),
    ("신청인", "[이름]"),
    ("신청인 이름", "[이름]"),
    ("신청인 성명", "[이름]"),
    ("실명", "[이름]"),
    ("대표전화", "[전화번호]"),
    ("대표 전화", "[전화번호]"),
    ("대표번호", "[전화번호]"),
    ("콜센터", "[전화번호]"),
    ("자택전화", "[전화번호]"),
    ("운전면허번호", "[여권·면허번호]"),
    ("상세주소", "[상세주소]"),
    ("사는 곳", "[상세주소]"),
    ("입금계좌", "[계좌번호]"),
    ("통장", "[계좌번호]"),
    ("통장번호", "[계좌번호]"),
)
_EXPLICIT_CONTEXT_LABEL: Final = re.compile(
    r"(?<![A-Z0-9가-힣\[])(?P<label>신청인\s+(?:이름|성명|성함)|식별번호|주민\s*등록\s*번호|주민\s*번호|"
    r"운전\s*면허(?:증)?(?:\s*번호)?|여권\s*번호|여권|면허(?:증)?\s*번호|대표\s+전화|대표전화|대표번호|자택전화|전화번호|연락처|전화|"
    r"휴대폰|콜센터|이메일|메일|상세주소|사는\s+곳|주소|거주지|입금계좌|계좌번호|"
    r"계좌|통장(?:번호)?|카드\s*번호|비밀번호|비번|패스워드|로그인\s*암호|"
    r"접속\s*암호|문자\s*인증\s*값|문자\s*확인\s*코드|"
    r"본인\s*인증\s*값|일회용\s*번호|인증\s*번호|"
    r"인증\s*코드|인증\s*문자|본인\s*확인\s*코드|보안\s*코드|"
    r"본인\s*인증용\s*확인\s*번호|(?:문자로\s+받은\s+)?6자리\s+코드|"
    r"확인\s*번호|인증\s*키|보안\s*키|"
    r"OTP(?:\s*번호)?|PIN(?:\s*번호)?|차량번호|번호판|"
    r"접수(?:\s*번호|\s*코드|\s*ID)|민원\s*번호|신청\s*번호|처리\s*번호|"
    r"배출(?:\s*신고)?\s*번호|진단명|복지대상|GPS|현재\s+위치|위치|"
    r"본명|실명|이름|성명|성함|신청인)"
    r"(?P<particle>은|는|이|가|을|를|인지)?(?![A-Z0-9가-힣])",
    re.IGNORECASE,
)
_ANY_FIXED_TOKEN: Final = re.compile(
    r"\[(?:이름|주민등록번호|여권·면허번호|전화번호|이메일|상세주소|계좌번호|"
    r"카드번호|인증정보|차량번호|접수번호|건강·복지정보|정밀위치)\]"
)
_SAFE_EXPLICIT_INQUIRY: Final = re.compile(
    r"^(?:어디(?:서|에서)\s+(?:확인|변경)하나요|어디(?:서|에서)\s+바꿔요|"
    r"어디에\s+쓰나요|"
    r"(?:변경|확인|발급)\s+방법(?:을)?\s+(?:알려주세요|알려줘)|"
    r"(?:바꾸는|변경하는)\s+방법(?:을)?\s+(?:알려주세요|알려줘)|"
    r"(?:바꾸|변경하)려면\s+어떻게\s+하나요|"
    r"등록\s+절차(?:를)?\s+(?:알려주세요|알려줘)|"
    r"어떻게\s+(?:확인|변경|등록|발급)하나요|어떻게\s+바꾸나요|"
    r"바꾸려면\s+어떻게\s+하나요|좀\s+알려주세요|"
    r"잊어버렸어요|잊어버렸는데\s+어떻게\s+해요|"
    r"변경은\s+어떻게\s+해요|기억나지\s+않아요|"
    r"이전은\s+어떻게\s+하나요|변경하려면\s+어디로\s+가나요|"
    r"번호\s+알려주세요|왜\s+입력해야\s+하나요|"
    r"확인할\s+수\s+있나요|궁금해요|어떻게\s+되나요|"
    r"꼭\s+필요한가요)[.?!]?\s*$"
)
_SAFE_VALUELESS_ADMIN_QUESTION: Final = re.compile(
    r"^(?:전입신고\s+후\s+주소\s+변경은\s+어떻게\s+하나요|"
    r"주소\s+변경을\s+언제까지\s+해야\s+하나요|"
    r"주소\s+변경\s+통보서비스는\s+어떻게\s+신청하나요|"
    r"전화번호\s+없이\s+전입신고할\s+수\s+있나요|"
    r"증명서에\s+주민번호가\s+모두\s+나오나요|"
    r"차량번호가\s+없어도\s+자동차세를\s+낼\s+수\s+있나요|"
    r"전입신고할\s+때\s+주소는\s+(?:어디까지\s+적어야\s+하나요|어떻게\s+적나요)|"
    r"대형폐기물\s+배출\s+주소는\s+수거\s+장소와\s+같아야\s+하나요|"
    r"자동차세\s+차량번호는\s+실제\s+번호판과\s+같아야\s+하나요|"
    r"전입신고\s+인증번호는\s+몇\s+분\s+동안\s+유효한가요|"
    r"지방세\s+납부\s+확인서에\s+이름이\s+나오나요|"
    r"전입신고서에\s+이름을\s+꼭\s+적어야\s+하나요|"
    r"지방세\s+고지서의\s+주소를\s+바꾸려면\s+어떻게\s+하나요|"
    r"전입신고\s+민원번호는\s+어디에\s+쓰나요|"
    r"증명서\s+이메일은\s+어디에서\s+변경하나요)[.?!]?\s*$"
)
_SAFE_VALUELESS_CONTEXT_SEGMENT: Final = re.compile(
    r"^(?=.{1,120}$)(?!.*(?:\d|@|\[|\]|[A-Z]))"
    r"(?=[가-힣\s]*?(?:어느|어디|언제|어떻게|왜|무엇|뭐|몇|얼마|없이|없어도|적지|"
    r"입력해야|잊|변경|확인|발급|번호|증명서|뒷자리|앞자리|꼭|처리|"
    r"보내야|바꾸면|바뀌|바꾸려면|바꿨는데|표시|가려|가린|유효|필요|"
    r"궁금|잘못|틀리|틀렸|달라|오류|누락|못|아직|모르|안\s+|등본에|"
    r"빼고|한글|대신|전송|다시|재설정|빠졌|직접|스티커|알림|오지|"
    r"기억|수정|그대로|고지|납세자|과\s+같아야|반드시|전체|써야|적어야|"
    r"공유|최신|비공개|필수|보관|취소|고치|정정|등록|초기화|늦게|"
    r"요청|기준|선택|들어가야|확정|가능|않|나중|바꿀))"
    r"[가-힣\s]*요[.?!]*\s*$"
)
_POSSIBLE_NAME_VALUE_QUESTION: Final = re.compile(
    rf"^[{_KOREAN_SURNAME_INITIALS}](?:\s*[가-힣]){{1,3}}\s*"
    r"(?:입니다|이에요|예요|인가요|맞나요)[.?!]?\s*$"
)
_SAFE_VALUELESS_LABEL_BRIDGE: Final = re.compile(
    r"^\s*(?!.*(?:\d|@|[A-Z]))(?:대신|납세자|"
    r"[가-힣\s]*(?:없으면|받을|관련|신청서에|때)[가-힣\s]*)\s*$"
)
_SAFE_SENSITIVE_CONTEXT_WORDS: Final = (
    (
        "[인증정보]",
        frozenset(
            {
                "궁금해요",
                "기억나지",
                "기존",
                "다시",
                "동안",
                "몇",
                "모르겠어요",
                "바꾸나요",
                "바꾸는",
                "바꿔요",
                "받을",
                "방법을",
                "방법이",
                "변경",
                "변경은",
                "변경하나요",
                "변경하려면",
                "보내주세요",
                "보내줄",
                "볼",
                "분",
                "설정하려면",
                "수",
                "신고를",
                "쓰나요",
                "아직",
                "안",
                "않아요",
                "알려주세요",
                "어디서",
                "어디에",
                "어디에서",
                "어떻게",
                "언제",
                "오나요",
                "오지",
                "왔어요",
                "유효한가요",
                "있나요",
                "잊어버렸는데",
                "잊어버렸어요",
                "잊었으면",
                "잊으면",
                "재설정하면",
                "재설정할",
                "하나요",
                "해요",
            }
        ),
    ),
    (
        "[이름]",
        frozenset(
            {
                "고칠",
                "꼭",
                "나오나요",
                "달라도",
                "발급되나요",
                "발급할",
                "수",
                "스티커에",
                "쓰나요",
                "어디에",
                "없이",
                "왜",
                "입력해야",
                "입력했어요",
                "있나요",
                "잘못",
                "적어야",
                "증명서를",
                "틀렸는데",
                "표시됐어요",
                "표시되나요",
                "필요한가요",
                "하나요",
                "한글로",
                "한글로만",
            }
        ),
    ),
    (
        "[건강·복지정보]",
        frozenset(
            {
                "방법",
                "수",
                "알려줘",
                "어디서",
                "어떻게",
                "있나요",
                "확인",
                "확인하나요",
                "확인할",
            }
        ),
    ),
)
_SAFE_CONTEXT_SUFFIX: Final = re.compile(
    r"^\s*(?:\(가명\)\s*)?(?:(?:입니다|이에요|예요|이고|라고(?:\s+합니다)?|"
    r"(?:을|를)\s+(?:입력|사용)했어요)\s*)?"
    r"[,.!?]*\s*$"
)
_SAFE_ADDRESS_SUFFIX: Final = re.compile(
    r"^\s*(?:(?:로\s+이사했어요|에\s+살아요|입니다|이에요|예요)\s*)?[,.!?]*\s*$"
)
_SAFE_PUBLIC_CONTEXT_SUFFIX: Final = re.compile(r"^\s+FAQ\s+확인\s*[,.!?]*\s*$")
_SAFE_CASE_CONTEXT_SUFFIX: Final = re.compile(
    r"^\s+(?:처리됐어|처리됐나요|처리되었나요|상태를?\s+확인해\s*줘)[.?!]*\s*$"
)
_SAFE_ADDRESS_VEHICLE_PREFIX: Final = re.compile(
    r"^(?:(?:세종특별자치시|세종시)\s+)?[가-힣0-9]+(?:대로|로|길)\s*$"
)
_SAFE_HEALTH_SUFFIX: Final = re.compile(
    r"^\s*(?:(?:입니다|이에요|예요|을\s+받았습니다|"
    r"(?:이|가)?\s*(?:있습니다|있어요)|했어요|"
    r"을\s+받고\s+(?:있습니다|있어요))\s*)?"
    r"[,.!?]*\s*$"
)
_SAFE_ADDRESS_PREFIX: Final = re.compile(
    r"^\s*(?:(?:제\s+)?주소(?:는)?|사는\s+곳|거주지|상세주소\s*[:：]?)?\s*$"
)
_SAFE_HEALTH_PREFIX: Final = re.compile(
    r"^\s*(?:저는|현재|진단(?:명)?(?:은|는|이|가)?\s*[:：]?|"
    r"복지대상(?:은|는|이|가)?\s*[:：]?)?\s*$"
)

_NON_NAME_GRAMMATICAL_ENDINGS: Final = frozenset("은는이가을를와과의에로만도한할해된될되며면고지")


def _match_bounds(match: re.Match[str]) -> tuple[int, int]:
    for group in ("value", "value_compass", "value_coords"):
        if match.groupdict().get(group) is not None:
            return match.span(group)
    return match.start("value_lat"), match.end("value_lng")


def _collect_findings(text: str) -> tuple[RedactionFinding, ...]:
    findings: list[RedactionFinding] = []
    for rule in _RULES:
        for match in rule.pattern.finditer(text):
            start, end = _match_bounds(match)
            if rule.category is PiiCategory.FINANCIAL_ACCOUNT:
                value = text[start:end]
                prefix = text[max(0, start - 24) : start]
                if re.fullmatch(r"\d{4}-\d{2}-\d{6}", value) and re.search(
                    rf"{_CASE_LABEL_PATTERN}(?:은|는|이|가)?\s*[:：]?\s*$",
                    prefix,
                    re.IGNORECASE,
                ):
                    continue
            if rule.category is PiiCategory.PAYMENT_CARD:
                skeleton = "".join(
                    character for character in text[start:end] if character.isdecimal()
                )
                prefix = text[max(0, start - 16) : start]
                has_explicit_card_context = (
                    re.search(r"(?:카드(?:\s*번호|는)?|결제\s*카드|계좌번호)\s*$", prefix)
                    is not None
                )
                if not _looks_like_payment_card(skeleton) and not has_explicit_card_context:
                    continue
                if re.search(r"(?:연도|금액|기간|문서번호)\s*$", prefix) and not (
                    _looks_like_payment_card(skeleton)
                ):
                    continue
            findings.append(
                RedactionFinding(rule.category, start, end, _replacement(rule.category))
            )
    return tuple(findings)


def _overlaps(left: RedactionFinding, right: RedactionFinding) -> bool:
    return left.start < right.end and right.start < left.end


def _select_findings(
    candidates: tuple[RedactionFinding, ...],
) -> tuple[RedactionFinding, ...]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            _CATEGORY_PRIORITY.index(item.category),
            -(item.end - item.start),
            item.start,
        ),
    )
    selected: list[RedactionFinding] = []
    for candidate in ranked:
        if not any(_overlaps(candidate, existing) for existing in selected):
            selected.append(candidate)
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                item.start,
                item.end,
                _CATEGORY_PRIORITY.index(item.category),
            ),
        )
    )


def _apply_findings(text: str, findings: tuple[RedactionFinding, ...]) -> str:
    masked = bytearray(text, "utf-8").decode("utf-8")
    for finding in reversed(findings):
        masked = masked[: finding.start] + finding.replacement + masked[finding.end :]
    return masked


def _has_uncovered_high_risk_span(
    text: str,
    findings: tuple[RedactionFinding, ...],
) -> bool:
    if _has_suspicious_identifier_mark(text):
        return True
    if _keycap_obscures_high_risk_shape(text):
        return True
    index = 0
    numeric_spans: list[tuple[int, int]] = []
    while index < len(text):
        if not text[index].isdecimal():
            index += 1
            continue
        start = index
        cursor = index
        digits: list[str] = []
        groups: list[int] = []
        current_group_length = 0
        last_digit_end = index
        while cursor < len(text):
            character = text[cursor]
            if character.isdecimal():
                digits.append(str(unicodedata.decimal(character)))
                current_group_length += 1
                last_digit_end = cursor + 1
                cursor += 1
                continue
            category = unicodedata.category(character)
            if category in {"Mn", "Me"}:
                cursor += 1
                continue
            if not character.isalnum():
                if current_group_length:
                    groups.append(current_group_length)
                    current_group_length = 0
                cursor += 1
                continue
            break
        if current_group_length:
            groups.append(current_group_length)
        skeleton = "".join(digits)
        if _is_high_risk_numeric_shape(groups, skeleton):
            numeric_spans.append((start, last_digit_end))
        index = max(cursor, index + 1)
    if _has_uncovered_spans(numeric_spans, findings):
        return True
    for pattern in _HIGH_RISK_SPAN_PATTERNS:
        if _has_uncovered_spans(
            (match.span() for match in pattern.finditer(text)),
            findings,
        ):
            return True
    return False


def _has_suspicious_identifier_mark(text: str) -> bool:
    for index, character in enumerate(text):
        if unicodedata.category(character) not in {"Mn", "Me"}:
            continue
        is_keycap_variation = (
            character == "\ufe0f"
            and index > 0
            and text[index - 1] in "0123456789#*"
            and index + 1 < len(text)
            and text[index + 1] == "\u20e3"
        )
        is_keycap_enclosure = (
            character == "\u20e3"
            and index > 0
            and (
                text[index - 1] in "0123456789#*"
                or (text[index - 1] == "\ufe0f" and index > 1 and text[index - 2] in "0123456789#*")
            )
        )
        if is_keycap_variation or is_keycap_enclosure:
            continue
        previous = text[index - 1] if index > 0 else ""
        following = text[index + 1] if index + 1 < len(text) else ""
        if _is_identifier_atom(previous) or _is_identifier_atom(following):
            return True
    return False


def _keycap_obscures_high_risk_shape(text: str) -> bool:
    if "\u20e3" not in text:
        return False
    without_keycaps = text.replace("\ufe0f", "").replace("\u20e3", "")
    return any(
        finding.category in {PiiCategory.PRECISE_LOCATION, PiiCategory.VEHICLE_PLATE}
        for finding in _collect_findings(without_keycaps)
    )


def _is_identifier_atom(character: str) -> bool:
    return bool(character) and (character.isalnum() or "가" <= character <= "힣")


def _is_high_risk_numeric_shape(groups: list[int], skeleton: str) -> bool:
    if any(length >= 10 for length in groups):
        return True
    if (
        (
            len(skeleton) in {10, 11}
            and skeleton[:3] in {"010", "011", "016", "017", "018", "019", "070"}
        )
        or (
            len(skeleton) in {11, 12}
            and len(skeleton) >= 4
            and skeleton[:4] in {"0502", "0503", "0504", "0505", "0506", "0507", "0508"}
        )
        or (len(skeleton) == 12 and skeleton.startswith("030"))
        or (len(skeleton) in {9, 10} and skeleton.startswith("02"))
        or (
            len(skeleton) in {10, 11}
            and len(skeleton) >= 3
            and skeleton[:3].isdigit()
            and 31 <= int(skeleton[1:3]) <= 65
            and skeleton.startswith("0")
        )
        or (len(skeleton) == 8 and skeleton[:2] in {"15", "16", "18"})
        or (len(skeleton) == 13 and skeleton[6] in "12345678")
        or _looks_like_payment_card(skeleton)
    ):
        return True
    digit_offset = 0
    for index, length in enumerate(groups):
        if groups[index : index + 4] in ([2, 2, 6, 2], [3, 6, 2, 3]):
            return True
        if groups[index : index + 3] == [3, 3, 6]:
            return True
        if groups[index : index + 3] == [3, 2, 6]:
            return True
        if groups[index : index + 2] == [4, 6]:
            return True
        if groups[index : index + 2] == [6, 7]:
            return True
        if groups[index : index + 3] == [4, 6, 5]:
            return True
        if groups[index : index + 4] == [4, 4, 4, 4] and _looks_like_payment_card(
            skeleton[digit_offset : digit_offset + 16]
        ):
            return True
        if (
            len(groups[index : index + 3]) == 3
            and length in {2, 3}
            and groups[index + 1] in {3, 4}
            and groups[index + 2] == 4
        ):
            return True
        if groups[index : index + 2] == [4, 4] and skeleton[digit_offset : digit_offset + 2] in {
            "15",
            "16",
            "18",
        }:
            return True
        digit_offset += length
    return False


def _passes_luhn(skeleton: str) -> bool:
    total = 0
    parity = len(skeleton) % 2
    for index, character in enumerate(skeleton):
        value = int(character)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _looks_like_payment_card(skeleton: str) -> bool:
    if len(skeleton) not in {13, 14, 15, 16, 17, 18, 19} or not _passes_luhn(skeleton):
        return False
    if len(skeleton) in {17, 18, 19}:
        return skeleton.startswith(
            ("4", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "62")
        )
    if len(skeleton) == 13:
        return skeleton.startswith("4")
    if len(skeleton) == 14:
        return skeleton.startswith(("300", "301", "302", "303", "304", "305", "36", "38", "39"))
    if len(skeleton) == 15:
        return skeleton.startswith(("34", "37"))
    if skeleton.startswith("4") or skeleton.startswith(
        (
            "51",
            "52",
            "53",
            "54",
            "55",
            "56",
            "57",
            "58",
            "59",
            "62",
            "65",
            "81",
            "82",
        )
    ):
        return True
    if 3528 <= int(skeleton[:4]) <= 3589:
        return True
    if skeleton.startswith("6011"):
        return True
    prefix = int(skeleton[:4])
    return 2221 <= prefix <= 2720


def _has_uncovered_spans(
    spans: Iterable[tuple[int, int]],
    findings: tuple[RedactionFinding, ...],
) -> bool:
    finding_index = 0
    for start, end in spans:
        while finding_index < len(findings) and findings[finding_index].end <= start:
            finding_index += 1
        if finding_index >= len(findings):
            return True
        finding = findings[finding_index]
        if finding.start > start or finding.end < end:
            return True
    return False


def _generated_token_spans(
    findings: tuple[RedactionFinding, ...],
) -> dict[tuple[int, int], PiiCategory]:
    offset = 0
    spans: dict[tuple[int, int], PiiCategory] = {}
    for finding in findings:
        start = finding.start + offset
        end = start + len(finding.replacement)
        spans[(start, end)] = finding.category
        offset += len(finding.replacement) - (finding.end - finding.start)
    return spans


def _has_unsafe_sensitive_finding_tail(
    text: str,
    findings: tuple[RedactionFinding, ...],
) -> bool:
    offset = 0
    ranges: list[tuple[int, int, PiiCategory]] = []
    for finding in findings:
        start = finding.start + offset
        end = start + len(finding.replacement)
        ranges.append((start, end, finding.category))
        offset += len(finding.replacement) - (finding.end - finding.start)
    for index, (start, end, category) in enumerate(ranges):
        if category not in {
            PiiCategory.DETAILED_ADDRESS,
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        }:
            continue
        sentence_start = (
            max(
                text.rfind(".", 0, start),
                text.rfind("!", 0, start),
                text.rfind("?", 0, start),
                text.rfind("\n", 0, start),
            )
            + 1
        )
        prefix = text[sentence_start:start]
        terminator = re.search(r"[.!?\n]", text[end:])
        segment_end = end + terminator.end() if terminator is not None else len(text)
        suffix_parts: list[str] = []
        cursor = end
        for next_start, next_end, _ in ranges[index + 1 :]:
            if next_start >= segment_end:
                break
            suffix_parts.append(text[cursor:next_start])
            cursor = min(next_end, segment_end)
        suffix_parts.append(text[cursor:segment_end])
        suffix = "".join(suffix_parts)
        if category is PiiCategory.DETAILED_ADDRESS:
            if not _SAFE_ADDRESS_PREFIX.fullmatch(prefix) or not _SAFE_ADDRESS_SUFFIX.fullmatch(
                suffix
            ):
                return True
        elif not _SAFE_HEALTH_PREFIX.fullmatch(prefix) or not _SAFE_HEALTH_SUFFIX.fullmatch(suffix):
            return True
        remainder_parts: list[str] = []
        cursor = end
        for next_start, next_end, _ in ranges[index + 1 :]:
            remainder_parts.append(text[cursor:next_start])
            cursor = next_end
        remainder_parts.append(text[cursor:])
        remainder = "".join(remainder_parts)
        if category is PiiCategory.DETAILED_ADDRESS and re.search(
            r"(?<!\d)\d+\s*(?:동|호|층)", remainder
        ):
            return True
        if category is PiiCategory.DETAILED_ADDRESS and re.search(
            r"(?:건물명|아파트명|동명)\s+[가-힣0-9]{2,30}", remainder
        ):
            return True
        if category is PiiCategory.SENSITIVE_HEALTH_WELFARE and re.search(
            r"(?<!\d)\d+\s*(?:형|기|급)", remainder
        ):
            return True
        if category is PiiCategory.SENSITIVE_HEALTH_WELFARE and re.search(
            r"(?:중증|말기|합병증(?:\s+있음)?)", remainder
        ):
            return True
    return False


def _normalized_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).casefold()


def _fixed_token_for_label(label: str) -> str | None:
    return next((token for candidate, token in _FIXED_TOKEN_BY_LABEL if candidate == label), None)


def _is_safe_explicit_inquiry(text: str) -> bool:
    if _SAFE_VALUELESS_ADMIN_QUESTION.fullmatch(text) is not None:
        return True
    label_match = _EXPLICIT_CONTEXT_LABEL.match(text)
    if label_match is None:
        return False
    segment = text[label_match.end() :]
    delimiter = re.match(r"\s*[:：]?\s*", segment)
    assert delimiter is not None
    return _SAFE_EXPLICIT_INQUIRY.fullmatch(segment[delimiter.end() :]) is not None


def _looks_like_contextual_person_name(candidate: str) -> bool:
    if (
        candidate in _SAFE_CONTEXTUAL_NAME_TERMS
        or candidate in _SAFE_STANDALONE_NAME_TERMS
        or candidate in _SAFE_ADMIN_LOCALITIES
    ):
        return False
    if candidate.startswith(tuple(_KOREAN_COMPOUND_SURNAMES.split("|"))):
        return True
    return candidate[-1] not in _NON_NAME_GRAMMATICAL_ENDINGS


def _is_safe_value_less_context_segment(content: str, expected_token: str | None) -> bool:
    if (
        _POSSIBLE_NAME_VALUE_QUESTION.fullmatch(content) is not None
        or _SAFE_VALUELESS_CONTEXT_SEGMENT.fullmatch(content) is None
    ):
        return False
    if expected_token == "[인증정보]" and re.search(
        r"(?:실제\s*비밀|비밀\s*값|암호\s*값)", content
    ):
        return False
    if expected_token == "[건강·복지정보]" and re.search(
        r"(?:암|당뇨|고혈압|천식|치매|우울증|희귀병|신장병|크론병|장애|"
        r"임신|투석|수급자|급여)",
        content,
    ):
        return False
    if expected_token == "[이름]":
        for match in _POSSIBLE_CONTEXTUAL_NAME_ANYWHERE.finditer(content):
            candidate = match.group("value")
            if _looks_like_contextual_person_name(candidate):
                return False
    return True


def _looks_like_unclassified_assignment(
    content: str,
    expected_token: str | None,
    delimiter: str,
) -> bool:
    stripped = content.strip()
    if not stripped:
        return False
    if ":" in delimiter or "：" in delimiter:
        return True
    if re.search(r"(?:\d|@|[A-Z])", stripped):
        return True
    if expected_token == "[인증정보]" and re.search(
        r"(?:실제\s*비밀|비밀\s*값|암호\s*값)", stripped
    ):
        return True
    if expected_token == "[건강·복지정보]" and re.search(
        r"(?:암|당뇨|고혈압|천식|치매|우울증|희귀병|신장병|크론병|장애|"
        r"임신|투석|수급자|급여)",
        stripped,
    ):
        return True
    if expected_token == "[이름]":
        for match in _POSSIBLE_CONTEXTUAL_NAME_ANYWHERE.finditer(stripped):
            candidate = match.group("value")
            if _looks_like_contextual_person_name(candidate):
                return True
    return False


def _has_unsafe_explicit_context(
    text: str,
    generated_spans: dict[tuple[int, int], PiiCategory],
) -> bool:
    fixed_tokens = iter(_ANY_FIXED_TOKEN.finditer(text))
    fixed_token = next(fixed_tokens, None)
    visible_labels: list[re.Match[str]] = []
    for label_match in _EXPLICIT_CONTEXT_LABEL.finditer(text):
        while fixed_token is not None and fixed_token.end() <= label_match.start():
            fixed_token = next(fixed_tokens, None)
        if fixed_token is not None and fixed_token.start() <= label_match.start():
            continue
        visible_labels.append(label_match)
    labels = tuple(visible_labels)
    for index, label_match in enumerate(labels):
        segment_end = labels[index + 1].start() if index + 1 < len(labels) else len(text)
        segment_start = label_match.end()
        segment = text[segment_start:segment_end]
        delimiter = re.match(r"\s*[:：]?\s*", segment)
        assert delimiter is not None
        content_start = segment_start + delimiter.end()
        content = text[content_start:segment_end]
        if not content or not content.strip(" \t\n,.!?"):
            continue
        if index + 1 < len(labels) and _SAFE_VALUELESS_LABEL_BRIDGE.fullmatch(content):
            continue
        if _SAFE_EXPLICIT_INQUIRY.fullmatch(content):
            continue
        token_match = _ANY_FIXED_TOKEN.search(content)
        if token_match is None:
            expected = _fixed_token_for_label(_normalized_label(label_match.group("label")))
            if _looks_like_unclassified_assignment(content, expected, delimiter.group()):
                return True
            continue
        token_span = (
            content_start + token_match.start(),
            content_start + token_match.end(),
        )
        is_generated = token_span in generated_spans
        prefix = content[: token_match.start()]
        if is_generated:
            label = _normalized_label(label_match.group("label"))
            is_address_vehicle_overlap = (
                label in {"주소", "상세주소", "거주지"}
                and generated_spans[token_span] is PiiCategory.VEHICLE_PLATE
                and _SAFE_ADDRESS_VEHICLE_PREFIX.fullmatch(prefix) is not None
            )
            if prefix.strip() and not is_address_vehicle_overlap:
                return True
        else:
            if prefix:
                return True
            expected = _fixed_token_for_label(_normalized_label(label_match.group("label")))
            if expected != token_match.group():
                return True
        suffix = content[token_match.end() :]
        if not (
            _SAFE_CONTEXT_SUFFIX.fullmatch(suffix)
            or _SAFE_PUBLIC_CONTEXT_SUFFIX.fullmatch(suffix)
            or (
                is_generated
                and generated_spans[token_span] is PiiCategory.CASE_REFERENCE
                and _SAFE_CASE_CONTEXT_SUFFIX.fullmatch(suffix)
            )
        ):
            return True
    return False


def _has_ambiguous_name(text: str) -> bool:
    possible = _POSSIBLE_KOREAN_NAME.fullmatch(text.strip())
    if possible is not None:
        candidate = re.sub(r"\s+", "", possible.group("value"))
        if candidate not in _SAFE_STANDALONE_NAME_TERMS and candidate not in _SAFE_ADMIN_LOCALITIES:
            return True
    for contextual in _POSSIBLE_CONTEXTUAL_NAME_ANYWHERE.finditer(text):
        candidate = contextual.group("value")
        if _looks_like_contextual_person_name(candidate):
            return True
    for label_match in _EXPLICIT_CONTEXT_LABEL.finditer(text):
        tail_contextual = _POSSIBLE_CONTEXTUAL_NAME_AT_END.search(text[: label_match.start()])
        if tail_contextual is None:
            continue
        candidate = tail_contextual.group("value")
        if _looks_like_contextual_person_name(candidate):
            return True
    for contextual in _POSSIBLE_CONTEXTUAL_NAME.finditer(text):
        candidate = next(value for value in contextual.groupdict().values() if value is not None)
        if _looks_like_contextual_person_name(candidate):
            return True
    for particle_name in _POSSIBLE_CONTEXTUAL_NAME_WITH_PARTICLE.finditer(text):
        if _looks_like_contextual_person_name(particle_name.group("value")):
            return True
    for match in _POSSIBLE_NAME_NEXT_TO_FIXED_TOKEN.finditer(text):
        candidate = match.group("before") or match.group("after")
        before_end = match.end("before") if match.group("before") is not None else -1
        candidate_is_label_tail = before_end >= 0 and any(
            label.end() == before_end
            for label in _EXPLICIT_CONTEXT_LABEL.finditer(text, 0, before_end)
        )
        if (
            candidate not in _SAFE_STANDALONE_NAME_TERMS
            and candidate not in _SAFE_ADMIN_LOCALITIES
            and not candidate_is_label_tail
            and not candidate.endswith(("대로", "로", "길", "시", "읍", "면"))
            and _EXPLICIT_CONTEXT_LABEL.fullmatch(candidate) is None
        ):
            return True
    for match in _AMBIGUOUS_NAME.finditer(text):
        honorific = match.groupdict().get("value")
        if honorific in _SAFE_STANDALONE_NAME_TERMS or honorific in _SAFE_ADMIN_LOCALITIES:
            continue
        standalone = match.groupdict().get("standalone_value")
        if standalone is not None and (
            standalone in _SAFE_STANDALONE_NAME_TERMS or standalone in _SAFE_ADMIN_LOCALITIES
        ):
            continue
        return True
    return False


def _has_ambiguous_address(text: str) -> bool:
    for match in _AMBIGUOUS_ADDRESS.finditer(text):
        if re.search(r"\[상세주소\]\s*,?\s*$", text[: match.start()]) is None:
            return True
    return False


def _has_compact_unclassified_tail(text: str) -> bool:
    match = re.search(r"[.!?]\s*(?P<tail>\S{1,64})\s*$", text)
    return match is not None and _ANY_FIXED_TOKEN.fullmatch(match.group("tail")) is None


def _redact_text(
    raw_text: str,
    *,
    reject_compact_unclassified_tail: bool,
    enforce_question_context_shape: bool,
) -> RedactionResult:
    normalized, reason = _normalize(raw_text)
    if reason is not None:
        return _closed(reason)
    assert normalized is not None
    if _is_safe_explicit_inquiry(normalized):
        return RedactionResult(normalized, (), True, True, None)
    findings = _select_findings(_collect_findings(normalized))
    if _has_uncovered_high_risk_span(normalized, findings):
        return _closed(UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN, findings)
    masked = _apply_findings(normalized, findings)
    if _has_ambiguous_address(masked):
        return _closed(UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS, findings)
    if enforce_question_context_shape and _has_unsafe_explicit_context(
        masked,
        _generated_token_spans(findings),
    ):
        return _closed(UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN, findings)
    if _has_ambiguous_name(masked):
        return _closed(UnresolvedReason.AMBIGUOUS_PERSON_NAME, findings)
    if _has_unsafe_sensitive_finding_tail(masked, findings):
        return _closed(UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN, findings)
    if (
        (reject_compact_unclassified_tail and _has_compact_unclassified_tail(masked))
        or _AMBIGUOUS_EXPLICIT_PII.search(masked)
        or _select_findings(_collect_findings(masked))
        or _has_uncovered_high_risk_span(masked, ())
    ):
        return _closed(UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN, findings)
    return RedactionResult(masked, findings, True, True, None)


def redact_question(raw_question: str) -> RedactionResult:
    return _redact_text(
        raw_question,
        reject_compact_unclassified_tail=True,
        enforce_question_context_shape=True,
    )


def redact_feedback_detail(raw_detail: str) -> RedactionResult:
    """Mask feedback prose while retaining all fixed and ambiguous PII gates."""

    return _redact_text(
        raw_detail,
        reject_compact_unclassified_tail=False,
        enforce_question_context_shape=False,
    )
