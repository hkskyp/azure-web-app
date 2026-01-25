# 성경 구절 데이터
# 이미지는 static/images/bible/ 에 저장 (Stable Diffusion으로 로컬 생성)

BIBLE_VERSES = [
    {
        "id": 1,
        "text": "여호와는 나의 목자시니 내게 부족함이 없으리로다",
        "reference": {"book": "시편", "chapter": 23, "verse": 1},
        "image": "psalm_23_1.webp",
        "blind_words": ["목자", "부족함"]
    },
    {
        "id": 2,
        "text": "내가 사망의 음침한 골짜기로 다닐지라도 해를 두려워하지 않을 것은 주께서 나와 함께 하심이라",
        "reference": {"book": "시편", "chapter": 23, "verse": 4},
        "image": "psalm_23_4.webp",
        "blind_words": ["사망", "골짜기", "함께"]
    },
    {
        "id": 3,
        "text": "하나님이 세상을 이처럼 사랑하사 독생자를 주셨으니 이는 그를 믿는 자마다 멸망하지 않고 영생을 얻게 하려 하심이라",
        "reference": {"book": "요한복음", "chapter": 3, "verse": 16},
        "image": "john_3_16.webp",
        "blind_words": ["사랑", "독생자", "영생"]
    },
    {
        "id": 4,
        "text": "내가 너희에게 새 계명을 주노니 서로 사랑하라 내가 너희를 사랑한 것 같이 너희도 서로 사랑하라",
        "reference": {"book": "요한복음", "chapter": 13, "verse": 34},
        "image": "john_13_34.webp",
        "blind_words": ["계명", "사랑"]
    },
    {
        "id": 5,
        "text": "수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라",
        "reference": {"book": "마태복음", "chapter": 11, "verse": 28},
        "image": "matthew_11_28.webp",
        "blind_words": ["수고", "무거운 짐", "쉬게"]
    },
    {
        "id": 6,
        "text": "너희가 내 안에 거하고 내 말이 너희 안에 거하면 무엇이든지 원하는 대로 구하라 그리하면 이루리라",
        "reference": {"book": "요한복음", "chapter": 15, "verse": 7},
        "image": "john_15_7.webp",
        "blind_words": ["거하고", "구하라", "이루리라"]
    },
    {
        "id": 7,
        "text": "너는 마음을 다하여 여호와를 신뢰하고 네 명철을 의지하지 말라",
        "reference": {"book": "잠언", "chapter": 3, "verse": 5},
        "image": "proverbs_3_5.webp",
        "blind_words": ["마음", "신뢰", "명철"]
    },
    {
        "id": 8,
        "text": "항상 기뻐하라 쉬지 말고 기도하라 범사에 감사하라",
        "reference": {"book": "데살로니가전서", "chapter": 5, "verse": 16},
        "image": "thessalonians_5_16.webp",
        "blind_words": ["기뻐하라", "기도하라", "감사하라"]
    },
    {
        "id": 9,
        "text": "내게 능력 주시는 자 안에서 내가 모든 것을 할 수 있느니라",
        "reference": {"book": "빌립보서", "chapter": 4, "verse": 13},
        "image": "philippians_4_13.webp",
        "blind_words": ["능력", "모든 것"]
    },
    {
        "id": 10,
        "text": "두려워하지 말라 내가 너와 함께 함이라 놀라지 말라 나는 네 하나님이 됨이라",
        "reference": {"book": "이사야", "chapter": 41, "verse": 10},
        "image": "isaiah_41_10.webp",
        "blind_words": ["두려워", "함께", "하나님"]
    },
    {
        "id": 11,
        "text": "그런즉 믿음은 들음에서 나며 들음은 그리스도의 말씀으로 말미암았느니라",
        "reference": {"book": "로마서", "chapter": 10, "verse": 17},
        "image": "romans_10_17.webp",
        "blind_words": ["믿음", "들음", "말씀"]
    },
    {
        "id": 12,
        "text": "너희 염려를 다 주께 맡기라 이는 그가 너희를 돌보심이라",
        "reference": {"book": "베드로전서", "chapter": 5, "verse": 7},
        "image": "peter_5_7.webp",
        "blind_words": ["염려", "맡기라", "돌보심"]
    },
    {
        "id": 13,
        "text": "주의 말씀은 내 발에 등이요 내 길에 빛이니이다",
        "reference": {"book": "시편", "chapter": 119, "verse": 105},
        "image": "psalm_119_105.webp",
        "blind_words": ["말씀", "등", "빛"]
    },
    {
        "id": 14,
        "text": "그러므로 우리가 믿음으로 의롭다 하심을 받았으니 우리 주 예수 그리스도로 말미암아 하나님과 화평을 누리자",
        "reference": {"book": "로마서", "chapter": 5, "verse": 1},
        "image": "romans_5_1.webp",
        "blind_words": ["믿음", "의롭다", "화평"]
    },
    {
        "id": 15,
        "text": "사람이 무엇으로 자기의 행실을 깨끗하게 하리이까 주의 말씀만 지킬 따름이니이다",
        "reference": {"book": "시편", "chapter": 119, "verse": 9},
        "image": "psalm_119_9.webp",
        "blind_words": ["행실", "깨끗하게", "말씀"]
    },
    {
        "id": 16,
        "text": "그가 찔림은 우리의 허물 때문이요 그가 상함은 우리의 죄악 때문이라",
        "reference": {"book": "이사야", "chapter": 53, "verse": 5},
        "image": "isaiah_53_5.webp",
        "blind_words": ["찔림", "허물", "상함", "죄악"]
    },
    {
        "id": 17,
        "text": "너희는 먼저 그의 나라와 그의 의를 구하라 그리하면 이 모든 것을 너희에게 더하시리라",
        "reference": {"book": "마태복음", "chapter": 6, "verse": 33},
        "image": "matthew_6_33.webp",
        "blind_words": ["나라", "의", "구하라"]
    },
    {
        "id": 18,
        "text": "여호와를 기뻐하는 것이 너희의 힘이니라",
        "reference": {"book": "느헤미야", "chapter": 8, "verse": 10},
        "image": "nehemiah_8_10.webp",
        "blind_words": ["여호와", "기뻐하는", "힘"]
    },
    {
        "id": 19,
        "text": "내가 선한 싸움을 싸우고 나의 달려갈 길을 마치고 믿음을 지켰으니",
        "reference": {"book": "디모데후서", "chapter": 4, "verse": 7},
        "image": "timothy_4_7.webp",
        "blind_words": ["선한 싸움", "달려갈 길", "믿음"]
    },
    {
        "id": 20,
        "text": "이는 우리가 믿음으로 행하고 보는 것으로 행하지 아니함이로라",
        "reference": {"book": "고린도후서", "chapter": 5, "verse": 7},
        "image": "corinthians_5_7.webp",
        "blind_words": ["믿음", "보는 것"]
    },
    {
        "id": 21,
        "text": "볼지어다 내가 문 밖에 서서 두드리노니 누구든지 내 음성을 듣고 문을 열면 내가 그에게로 들어가리라",
        "reference": {"book": "요한계시록", "chapter": 3, "verse": 20},
        "image": "revelation_3_20.webp",
        "blind_words": ["문", "두드리노니", "음성", "들어가리라"]
    },
    {
        "id": 22,
        "text": "악을 미워하고 선을 사랑하며 성문에서 정의를 세울지어다",
        "reference": {"book": "아모스", "chapter": 5, "verse": 15},
        "image": "amos_5_15.webp",
        "blind_words": ["악", "선", "정의"]
    },
    {
        "id": 23,
        "text": "나의 은혜가 네게 족하도다 이는 내 능력이 약한 데서 온전하여짐이라",
        "reference": {"book": "고린도후서", "chapter": 12, "verse": 9},
        "image": "corinthians_12_9.webp",
        "blind_words": ["은혜", "족하도다", "능력", "온전"]
    },
    {
        "id": 24,
        "text": "네 시작은 미약하였으나 네 나중은 심히 창대하리라",
        "reference": {"book": "욥기", "chapter": 8, "verse": 7},
        "image": "job_8_7.webp",
        "blind_words": ["시작", "미약", "나중", "창대"]
    },
    {
        "id": 25,
        "text": "사랑하는 자들아 우리가 서로 사랑하자 사랑은 하나님께 속한 것이니",
        "reference": {"book": "요한일서", "chapter": 4, "verse": 7},
        "image": "john1_4_7.webp",
        "blind_words": ["사랑", "하나님"]
    },
    {
        "id": 26,
        "text": "주께서 내게 이르시되 내 은혜가 네게 족하도다",
        "reference": {"book": "고린도후서", "chapter": 12, "verse": 9},
        "image": "corinthians_12_9_alt.webp",
        "blind_words": ["은혜", "족하도다"]
    },
    {
        "id": 27,
        "text": "모든 것을 참으며 모든 것을 믿으며 모든 것을 바라며 모든 것을 견디느니라",
        "reference": {"book": "고린도전서", "chapter": 13, "verse": 7},
        "image": "corinthians1_13_7.webp",
        "blind_words": ["참으며", "믿으며", "바라며", "견디느니라"]
    },
    {
        "id": 28,
        "text": "여호와께서 너를 지키시되 네 우편에서 네 그늘이 되시나니",
        "reference": {"book": "시편", "chapter": 121, "verse": 5},
        "image": "psalm_121_5.webp",
        "blind_words": ["지키시되", "그늘"]
    },
    {
        "id": 29,
        "text": "평강하게 하는 자는 복이 있나니 그들이 하나님의 아들이라 일컬음을 받을 것임이요",
        "reference": {"book": "마태복음", "chapter": 5, "verse": 9},
        "image": "matthew_5_9.webp",
        "blind_words": ["평강", "복", "하나님의 아들"]
    },
    {
        "id": 30,
        "text": "그러므로 형제들아 내가 하나님의 모든 자비하심으로 너희를 권하노니 너희 몸을 하나님이 기뻐하시는 거룩한 산 제물로 드리라",
        "reference": {"book": "로마서", "chapter": 12, "verse": 1},
        "image": "romans_12_1.webp",
        "blind_words": ["자비", "거룩한", "산 제물"]
    },
    {
        "id": 31,
        "text": "보라 형제가 연합하여 동거함이 어찌 그리 선하고 아름다운고",
        "reference": {"book": "시편", "chapter": 133, "verse": 1},
        "image": "psalm_133_1.webp",
        "blind_words": ["연합", "동거", "선하고", "아름다운"]
    },
    {
        "id": 32,
        "text": "죽도록 충성하라 그리하면 내가 생명의 관을 네게 주리라",
        "reference": {"book": "요한계시록", "chapter": 2, "verse": 10},
        "image": "revelation_2_10.webp",
        "blind_words": ["충성", "생명의 관"]
    },
    {
        "id": 33,
        "text": "너희 안에 이 마음을 품으라 곧 그리스도 예수의 마음이니",
        "reference": {"book": "빌립보서", "chapter": 2, "verse": 5},
        "image": "philippians_2_5.webp",
        "blind_words": ["마음", "그리스도", "예수"]
    },
    {
        "id": 34,
        "text": "여호와는 나의 빛이요 나의 구원이시니 내가 누구를 두려워하리요",
        "reference": {"book": "시편", "chapter": 27, "verse": 1},
        "image": "psalm_27_1.webp",
        "blind_words": ["빛", "구원", "두려워"]
    },
    {
        "id": 35,
        "text": "스스로 속이지 말라 하나님은 만홀히 여김을 받지 아니하시나니 사람이 무엇으로 심든지 그대로 거두리라",
        "reference": {"book": "갈라디아서", "chapter": 6, "verse": 7},
        "image": "galatians_6_7.webp",
        "blind_words": ["속이지", "심든지", "거두리라"]
    },
    {
        "id": 36,
        "text": "오직 성령의 열매는 사랑과 희락과 화평과 오래 참음과 자비와 양선과 충성과",
        "reference": {"book": "갈라디아서", "chapter": 5, "verse": 22},
        "image": "galatians_5_22.webp",
        "blind_words": ["성령", "열매", "사랑", "화평"]
    },
    {
        "id": 37,
        "text": "이는 내 아버지의 뜻이 아들을 보고 믿는 자마다 영생을 얻는 이것이니",
        "reference": {"book": "요한복음", "chapter": 6, "verse": 40},
        "image": "john_6_40.webp",
        "blind_words": ["아버지", "뜻", "믿는", "영생"]
    },
    {
        "id": 38,
        "text": "여호와를 경외하는 것이 지혜의 근본이요 거룩하신 자를 아는 것이 명철이니라",
        "reference": {"book": "잠언", "chapter": 9, "verse": 10},
        "image": "proverbs_9_10.webp",
        "blind_words": ["경외", "지혜", "명철"]
    },
    {
        "id": 39,
        "text": "예수께서 이르시되 나는 부활이요 생명이니 나를 믿는 자는 죽어도 살겠고",
        "reference": {"book": "요한복음", "chapter": 11, "verse": 25},
        "image": "john_11_25.webp",
        "blind_words": ["부활", "생명", "믿는"]
    },
    {
        "id": 40,
        "text": "또 너희가 무엇을 하든지 말에나 일에나 다 주 예수의 이름으로 하고 그를 힘입어 하나님 아버지께 감사하라",
        "reference": {"book": "골로새서", "chapter": 3, "verse": 17},
        "image": "colossians_3_17.webp",
        "blind_words": ["예수", "이름", "감사"]
    },
    {
        "id": 41,
        "text": "내 영혼아 여호와를 송축하라 그의 모든 은택을 잊지 말지어다",
        "reference": {"book": "시편", "chapter": 103, "verse": 2},
        "image": "psalm_103_2.webp",
        "blind_words": ["영혼", "송축", "은택"]
    },
    {
        "id": 42,
        "text": "범사에 감사하라 이것이 그리스도 예수 안에서 너희를 향하신 하나님의 뜻이니라",
        "reference": {"book": "데살로니가전서", "chapter": 5, "verse": 18},
        "image": "thessalonians_5_18.webp",
        "blind_words": ["범사", "감사", "뜻"]
    },
    {
        "id": 43,
        "text": "의인의 기도는 역사하는 힘이 큼이니라",
        "reference": {"book": "야고보서", "chapter": 5, "verse": 16},
        "image": "james_5_16.webp",
        "blind_words": ["의인", "기도", "역사", "힘"]
    },
    {
        "id": 44,
        "text": "그런즉 이와 같이 믿음도 행함이 없으면 그 자체가 죽은 것이라",
        "reference": {"book": "야고보서", "chapter": 2, "verse": 17},
        "image": "james_2_17.webp",
        "blind_words": ["믿음", "행함", "죽은"]
    },
    {
        "id": 45,
        "text": "자녀들아 우리가 말과 혀로만 사랑하지 말고 행함과 진실함으로 하자",
        "reference": {"book": "요한일서", "chapter": 3, "verse": 18},
        "image": "john1_3_18.webp",
        "blind_words": ["말", "혀", "행함", "진실"]
    },
    {
        "id": 46,
        "text": "너희는 유혹의 시험을 당할 때에 온전히 기쁘게 여기라",
        "reference": {"book": "야고보서", "chapter": 1, "verse": 2},
        "image": "james_1_2.webp",
        "blind_words": ["유혹", "시험", "기쁘게"]
    },
    {
        "id": 47,
        "text": "그러므로 주 안에서 사랑을 받는 형제들아 견고하며 흔들리지 말고 항상 주의 일에 더욱 힘쓰는 자들이 되라",
        "reference": {"book": "고린도전서", "chapter": 15, "verse": 58},
        "image": "corinthians1_15_58.webp",
        "blind_words": ["견고", "흔들리지", "힘쓰는"]
    },
    {
        "id": 48,
        "text": "주는 영이시니 주의 영이 계신 곳에는 자유가 있느니라",
        "reference": {"book": "고린도후서", "chapter": 3, "verse": 17},
        "image": "corinthians2_3_17.webp",
        "blind_words": ["영", "자유"]
    },
    {
        "id": 49,
        "text": "너희가 내 이름으로 무엇을 구하든지 내가 행하리니 이는 아버지로 하여금 아들로 말미암아 영광을 받으시게 하려 함이라",
        "reference": {"book": "요한복음", "chapter": 14, "verse": 13},
        "image": "john_14_13.webp",
        "blind_words": ["이름", "구하든지", "영광"]
    },
    {
        "id": 50,
        "text": "하늘에 계신 우리 아버지여 이름이 거룩히 여김을 받으시오며 나라가 임하시오며 뜻이 하늘에서 이루어진 것 같이 땅에서도 이루어지이다",
        "reference": {"book": "마태복음", "chapter": 6, "verse": 9},
        "image": "matthew_6_9.webp",
        "blind_words": ["아버지", "거룩", "나라", "뜻"]
    },
]
