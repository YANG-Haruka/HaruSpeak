from __future__ import annotations

from ..base import ErrorPattern, ErrorPatternLib


_PATTERNS: dict[str, list[ErrorPattern]] = {
    "ja": [
        ErrorPattern(
            symptom="平音・激音・濃音の三系列を使い分けられない（가/카/까 が同じに聞こえる）",
            cause="日本語に対応する三項対立がなく、清濁の二項に投影してしまう",
            hint="激音は強い息、濃音は喉を緊張させて息を出さない、平音は無気で柔らかく",
        ),
        ErrorPattern(
            symptom="終声 (パッチム) の k/t/p を破裂させて発音する",
            cause="日本語の促音は次の子音への準備、韓国語のパッチムは閉鎖のみ（不破裂）",
            hint="입 (ip) を「イプ」ではなく [ip˺]、唇を閉じたまま止める",
        ),
        ErrorPattern(
            symptom="ㅓ と ㅗ の区別ができない（서울 が ソール になる）",
            cause="日本語の「お」一つに ㅓ [ʌ] と ㅗ [o] を吸収してしまう",
            hint="ㅓ は口を縦に大きく開けて喉の奥から、ㅗ は唇を丸めて前へ",
        ),
    ],
    "zh": [
        ErrorPattern(
            symptom="평음・격음・경음을 무성/유성처럼 다루어 평음을 너무 강하게 발음",
            cause="중국어의 송기/불송기 대립을 한국어의 삼항 대립에 직접 매핑함",
            hint="평음은 약하게, 격음은 강한 숨, 경음은 목을 긴장시키고 숨 없이",
        ),
        ErrorPattern(
            symptom="종성 ㄴ 과 ㅇ 의 구별이 잘 안 된다 (안 vs 앙)",
            cause="중국어의 -n 과 -ng 도 같은 문제로 학습자에 따라 흐려짐",
            hint="ㄴ 은 혀끝을 윗잇몸에, ㅇ 은 혀뿌리를 연구개에 — 입을 다물지 말 것",
        ),
        ErrorPattern(
            symptom="한국어 문장에 중국어식 성조를 얹는다",
            cause="모국어의 lexical tone 습관이 외국어 발화에 그대로 따라온다",
            hint="한국어는 음높이가 어휘 의미를 바꾸지 않음 — 평탄하게 자연스러운 억양으로",
        ),
    ],
    "en": [
        ErrorPattern(
            symptom="Pronouncing ㅓ as English 'aw' or ㅗ as 'oh' diphthong",
            cause="English vowels glide; Korean monophthongs are pure",
            hint="Hold ㅓ [ʌ] and ㅗ [o] steady — no glide off the end",
        ),
        ErrorPattern(
            symptom="Aspirating all stops like English (treating 가 as English 'k')",
            cause="English /k t p/ are aspirated word-initially; Korean has 3-way contrast",
            hint="Plain ㄱㄷㅂ are *unaspirated* — softer than English equivalents",
        ),
        ErrorPattern(
            symptom="Releasing final stops audibly (입 → 'ip-uh', 책 → 'chek-uh')",
            cause="English speakers tend to release final consonants with a small vowel",
            hint="Close the mouth/lips and stop airflow — no audible release",
        ),
    ],
}


def common_errors(l1: str) -> ErrorPatternLib:
    return ErrorPatternLib(l1=l1, l2="ko", patterns=_PATTERNS.get(l1, []))
