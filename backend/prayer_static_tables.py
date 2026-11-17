"""Official city prayer-time tables from the reference application.

Generated from the packaged Salati 2.0.2 database (``staticprayertimes``).
The reference stores a full year of official clock times per city (standard
time, DST added by the platform).  Rather than shipping those clock times
verbatim -- which would break whenever a country changes its UTC offset or
DST rules -- this module stores the minute difference between the official
table and our solar engine for the same calendar day.  Adding that delta to
the engine keeps the official local clock reading while following the
current time-zone rules.

The data is zlib-compressed JSON plus base85; it is decoded lazily on the
first static-city lookup.
"""

import base64
import json
import zlib
from datetime import date
from typing import Optional, Tuple

# Calendar order used by the reference tables (includes a synthetic Feb 29).
_MMDD = (
    "0101",
    "0102",
    "0103",
    "0104",
    "0105",
    "0106",
    "0107",
    "0108",
    "0109",
    "0110",
    "0111",
    "0112",
    "0113",
    "0114",
    "0115",
    "0116",
    "0117",
    "0118",
    "0119",
    "0120",
    "0121",
    "0122",
    "0123",
    "0124",
    "0125",
    "0126",
    "0127",
    "0128",
    "0129",
    "0130",
    "0131",
    "0201",
    "0202",
    "0203",
    "0204",
    "0205",
    "0206",
    "0207",
    "0208",
    "0209",
    "0210",
    "0211",
    "0212",
    "0213",
    "0214",
    "0215",
    "0216",
    "0217",
    "0218",
    "0219",
    "0220",
    "0221",
    "0222",
    "0223",
    "0224",
    "0225",
    "0226",
    "0227",
    "0228",
    "0229",
    "0301",
    "0302",
    "0303",
    "0304",
    "0305",
    "0306",
    "0307",
    "0308",
    "0309",
    "0310",
    "0311",
    "0312",
    "0313",
    "0314",
    "0315",
    "0316",
    "0317",
    "0318",
    "0319",
    "0320",
    "0321",
    "0322",
    "0323",
    "0324",
    "0325",
    "0326",
    "0327",
    "0328",
    "0329",
    "0330",
    "0331",
    "0401",
    "0402",
    "0403",
    "0404",
    "0405",
    "0406",
    "0407",
    "0408",
    "0409",
    "0410",
    "0411",
    "0412",
    "0413",
    "0414",
    "0415",
    "0416",
    "0417",
    "0418",
    "0419",
    "0420",
    "0421",
    "0422",
    "0423",
    "0424",
    "0425",
    "0426",
    "0427",
    "0428",
    "0429",
    "0430",
    "0501",
    "0502",
    "0503",
    "0504",
    "0505",
    "0506",
    "0507",
    "0508",
    "0509",
    "0510",
    "0511",
    "0512",
    "0513",
    "0514",
    "0515",
    "0516",
    "0517",
    "0518",
    "0519",
    "0520",
    "0521",
    "0522",
    "0523",
    "0524",
    "0525",
    "0526",
    "0527",
    "0528",
    "0529",
    "0530",
    "0531",
    "0601",
    "0602",
    "0603",
    "0604",
    "0605",
    "0606",
    "0607",
    "0608",
    "0609",
    "0610",
    "0611",
    "0612",
    "0613",
    "0614",
    "0615",
    "0616",
    "0617",
    "0618",
    "0619",
    "0620",
    "0621",
    "0622",
    "0623",
    "0624",
    "0625",
    "0626",
    "0627",
    "0628",
    "0629",
    "0630",
    "0701",
    "0702",
    "0703",
    "0704",
    "0705",
    "0706",
    "0707",
    "0708",
    "0709",
    "0710",
    "0711",
    "0712",
    "0713",
    "0714",
    "0715",
    "0716",
    "0717",
    "0718",
    "0719",
    "0720",
    "0721",
    "0722",
    "0723",
    "0724",
    "0725",
    "0726",
    "0727",
    "0728",
    "0729",
    "0730",
    "0731",
    "0801",
    "0802",
    "0803",
    "0804",
    "0805",
    "0806",
    "0807",
    "0808",
    "0809",
    "0810",
    "0811",
    "0812",
    "0813",
    "0814",
    "0815",
    "0816",
    "0817",
    "0818",
    "0819",
    "0820",
    "0821",
    "0822",
    "0823",
    "0824",
    "0825",
    "0826",
    "0827",
    "0828",
    "0829",
    "0830",
    "0831",
    "0901",
    "0902",
    "0903",
    "0904",
    "0905",
    "0906",
    "0907",
    "0908",
    "0909",
    "0910",
    "0911",
    "0912",
    "0913",
    "0914",
    "0915",
    "0916",
    "0917",
    "0918",
    "0919",
    "0920",
    "0921",
    "0922",
    "0923",
    "0924",
    "0925",
    "0926",
    "0927",
    "0928",
    "0929",
    "0930",
    "1001",
    "1002",
    "1003",
    "1004",
    "1005",
    "1006",
    "1007",
    "1008",
    "1009",
    "1010",
    "1011",
    "1012",
    "1013",
    "1014",
    "1015",
    "1016",
    "1017",
    "1018",
    "1019",
    "1020",
    "1021",
    "1022",
    "1023",
    "1024",
    "1025",
    "1026",
    "1027",
    "1028",
    "1029",
    "1030",
    "1031",
    "1101",
    "1102",
    "1103",
    "1104",
    "1105",
    "1106",
    "1107",
    "1108",
    "1109",
    "1110",
    "1111",
    "1112",
    "1113",
    "1114",
    "1115",
    "1116",
    "1117",
    "1118",
    "1119",
    "1120",
    "1121",
    "1122",
    "1123",
    "1124",
    "1125",
    "1126",
    "1127",
    "1128",
    "1129",
    "1130",
    "1201",
    "1202",
    "1203",
    "1204",
    "1205",
    "1206",
    "1207",
    "1208",
    "1209",
    "1210",
    "1211",
    "1212",
    "1213",
    "1214",
    "1215",
    "1216",
    "1217",
    "1218",
    "1219",
    "1220",
    "1221",
    "1222",
    "1223",
    "1224",
    "1225",
    "1226",
    "1227",
    "1228",
    "1229",
    "1230",
    "1231",
)

_DAY_INDEX = {md: i for i, md in enumerate(_MMDD)}

# (country_code, normalized city name) -> table key
_CITY_INDEX = {
    ("AE", "abudhabi"): "abudhabi",
    ("AE", "ajman"): "ajman",
    ("AE", "alain"): "alain",
    ("AE", "dubai"): "dubai",
    ("AE", "fujairah"): "fujairah",
    ("AE", "khawrfakkan"): "KhawrFakkan",
    ("AE", "rasalkhaimah"): "rasalkhaimah",
    ("AE", "sharjah"): "sharjah",
    ("AE", "ummalquwain"): "ummalquwain",
    ("AT", "graz"): "graz",
    ("AT", "innsbruck"): "innsbruck",
    ("AT", "klagenfurt"): "klagenfurt",
    ("AT", "linz"): "linz",
    ("AT", "salzburg"): "salzburg",
    ("AT", "sanktpolten"): "sanktpolten",
    ("AT", "vienna"): "vienna",
    ("BE", "brussels"): "brussels",
    ("CA", "calgary"): "calgary",
    ("CA", "mississauga"): "mississauga",
    ("CA", "montreal"): "montreal",
    ("CA", "windsor"): "windsor",
    ("DE", "aachen"): "aachen",
    ("DE", "berlin"): "berlin",
    ("DE", "halle"): "halle",
    ("DE", "hamburg"): "hamburg",
    ("DE", "munich"): "munchen",
    ("DE", "nuremberg"): "nuremberg",
    ("DE", "potsdam"): "potsdam",
    ("FR", "lyon"): "lyon",
    ("FR", "paris"): "paris",
    ("FR", "toulouse"): "toulouse",
    ("GB", "birmingham"): "birmingham",
    ("GB", "london"): "london",
    ("IQ", "baghdad"): "baghdad",
    ("IQ", "dahuk"): "duhok",
    ("IQ", "erbil"): "erbil",
    ("IQ", "kirkuk"): "kirkuk",
    ("IQ", "samarra"): "samarra",
    ("IQ", "sulaymaniyah"): "sulaymaniyah",
    ("LU", "luxembourg"): "luxembourg",
    ("LY", "ajdabiya"): "ajdabiya",
    ("LY", "albayda"): "bayda",
    ("LY", "azzawiya"): "zawia",
    ("LY", "azzawiyah"): "zawia",
    ("LY", "bayda"): "bayda",
    ("LY", "benghazi"): "benghazi",
    ("LY", "misrata"): "misrata",
    ("LY", "tobruk"): "tobruk",
    ("LY", "tripoli"): "tripoli",
    ("LY", "zawiya"): "zawia",
    ("LY", "zliten"): "zliten",
    ("SY", "aleppo"): "aleppo",
    ("SY", "damascus"): "damascus",
    ("SY", "deirezzor"): "deirezzor",
    ("SY", "hama"): "hama",
    ("SY", "homs"): "homs",
    ("SY", "latakia"): "latakia",
    ("TJ", "dushanbe"): "dushanbe",
}

# table key -> (baseline method key, reference altitude in metres)
_CITY_INFO = {
    "KhawrFakkan": ("emirates", 20.0),
    "aachen": ("aachen", 178.0),
    "abudhabi": ("emirates", 6.0),
    "ajdabiya": ("libya", 3.0),
    "ajman": ("emirates", 4.0),
    "alain": ("emirates", 275.0),
    "aleppo": ("syria", 401.0),
    "baghdad": ("iraq", 41.0),
    "bayda": ("libya", 0.0),
    "benghazi": ("libya", 4.0),
    "berlin": ("aachen", 43.0),
    "birmingham": ("birmingham", 149.0),
    "brussels": ("belgium", 28.0),
    "calgary": ("calgary", 1042.0),
    "damascus": ("syria", 701.0),
    "deirezzor": ("syria", 210.0),
    "dubai": ("emirates", 3.0),
    "duhok": ("iraq", 0.0),
    "dushanbe": ("tajikistan", 767.0),
    "erbil": ("iraq", 426.0),
    "fujairah": ("emirates", 20.0),
    "graz": ("austria", 363.0),
    "halle": ("aachen", 96.0),
    "hama": ("syria", 0.0),
    "hamburg": ("aachen", 8.0),
    "homs": ("syria", 513.0),
    "innsbruck": ("austria", 587.0),
    "kirkuk": ("iraq", 346.0),
    "klagenfurt": ("austria", 450.0),
    "latakia": ("syria", 29.0),
    "linz": ("austria", 268.0),
    "london": ("london", 25.0),
    "luxembourg": ("luxembourg", 316.0),
    "lyon": ("lyon", 173.0),
    "misrata": ("libya", 0.0),
    "mississauga": ("mississauga", 159.0),
    "montreal": ("montreal", 216.0),
    "munchen": ("munchen", 524.0),
    "nuremberg": ("aachen", 312.0),
    "paris": ("paris", 42.0),
    "potsdam": ("aachen", 34.0),
    "rasalkhaimah": ("emirates", 2.0),
    "salzburg": ("austria", 435.0),
    "samarra": ("iraq", 0.0),
    "sanktpolten": ("austria", 275.0),
    "sharjah": ("emirates", 6.0),
    "sulaymaniyah": ("iraq", 0.0),
    "tobruk": ("libya", 20.0),
    "toulouse": ("toulouse", 150.0),
    "tripoli": ("libya", 21.0),
    "ummalquwain": ("emirates", 0.0),
    "vienna": ("austria", 193.0),
    "windsor": ("windsor", 11.0),
    "zawia": ("libya", 18.0),
    "zliten": ("libya", 9.0),
}

_PACKED = (
    "c-qXp*^(u>aVYpN{hVnA#~LxeBI}2u$Wgb%Mb;v1Oq!pcJ`q@a1rR4wykk{amGB)q;En+P-=BW`;U9ne<;Nd>{ptVumw#~|@ZmoE"
    "@BhNjAOG_D9X>)$xeteM?!pbq7i~~+lJ7<7x(2EbQv%Tr4Ce?=QaTeCHY{_~yldLsM5ZPMm}R;?kMudCl%xh{YVccDW0^o?>Nv{h"
    "P@Awy0!UedS`S{y1JpctrEXgZdQlQXgE#EdOHj6CyDc@DPAMf2?b=RJ?cB0i`)p<Q4xg@1Qo`Go&BhR~mb_y)+yj8MK|Q69M6=ww"
    "WxwTpOtZz-Fdr4|^7Lj8=j|+z@x`lc5ElIpSPzhvIb%$gqqo}{O?{`dd(IeboSGwA4}fIS9KmGN*R;FoSm#9jfiXrpL%ThTx?X}X"
    "9e3?=;qx>t7clz~*RJJ{mzfhiVDt{R7*T*p0Tah(E||87d3&)a^%2D>wW;@MXK0u06I7WRpA)t?L&~f+HA)b9*lTA_sg;2Pvz7Ba"
    "$TD-&^`Nc+ruC<fHnX*j);{%;aEjIQxno_rvvFP<v%JwhL7h|edIyuzp8xph&9&270mU+B<RMH(DQnKr)^1K+o66PbtUuVR?R`o&"
    "UGwcz`U&N%--b8KjJFAA>?Y>>IJ)-U%fo#Cuvaen=;qjp)026{-aoj>-pQ#un^vBlNbwU}wEV5wyj3oGy?b+Po%NjA&UCh#8TkWq"
    "Z||nNy4lWq)ymzMrGT+t0kIo|#k{$mWwcUS&7y06h+C{U{nl=2zN%dHX}8=d!gOR<d7HxHz5<i{!Llvwl&<D4_->qA)XLt-F!+A{"
    "_~{S7{`Qw&|N3vg{P@euCFskCtAAd!SMn3?e>%XSbbkFtD6*g+5)+r02EF41P9un2AW2H}C$w~vHy{oHJ~80c*?qt~7sPWC3<wR-"
    "c>*ViHvlLAI0axKiIZFahXC0C3^nD|Hcl+{xFLh&Xe14Az5oXT9D4xNHg3J6akvWU?aAG?Lf!&Yxv%^~>gZY`kXaECK)iVrKrayr"
    "aS9-)0Myb*x-|gc?Fs_6y+WK0a54=|W*5S&0A7>O8Z!YLw8w<N(jKYsn4qQoNWY3I@Mau5Ym$Mq>sLz%Zpb)T`ebQ<1{nSL>VqV!"
    "5kp?E!~sR{9IQA#y~B`KexWh-5(%6n3MrYB6b?8UAUG~0c%u0NMb1?fefAm%Rnw<OY$u_*YN=*xFvid!y&Lc%MKsPL$-KN`5lp1Q"
    "U!B&G3V!wUTIGW&c>xKy?Y+dL8-TKqatAf8<8Gh`a^g1rYO&A&eIN=qWH9BcohJ;*H)Mz@4ba70n#L4c0l5Ckt0*GQW_ei?aTdzU"
    "ni$C78gJ0hRbGV=)6i93=0v2tyh<YBe&{gZHLAZ<C)C@Im*#|rpyMSq;X(U&l|w2Y-Q44BB&~m6dXQ;1g-41n(*RKjTVGn@$pJ{q"
    "!3*FrK1L3}TKrx3!;Y(Ao~(#M<^WvGCmS)Zau2`&xX+YK*GYHX;e|{gO97~WKGgf#0In(d6Dmn0(<#(;Lne?Lf|~vfz>2O($T7fy"
    "(yum>M{Vb;rasW{b3r13TqSV(g9gB1z^h0;@2v!egpWS8<a96H{ODdCf;;I$KoC+dNW!KN$bzI5e)cxREdZVZa<h&=h%E{LHYmDO"
    "!qWi-4Q^HM7|N=xj<VqP*9yha($B4^p;aL!=>VWL=6E|mD~@zG6(<_ckW$;%0F=Hp8qK)jdn@)Ba9+)tj^%hDa977bOX62gDI9>;"
    "Beb)9ivIZ7yLH4%e6hs61{As+&wOcE#NOeW56GtFhTx*TMmN00y9YqLEv!SL6A--nxgl8cHP?h9AP3pI^a1(?`8J3X*`dva9TM?W"
    "FdzkUc|1LK{e<hveI$E_dsYp+U}NAF6oFT3bi6G@_W?+>Yx#G$$&E7dZH>|M(IJ^PehR6J7og)6sgJ8ahlq>1fe@Rh#<7?h+t}j<"
    "4IA4U46zlyk4RZ8e-mFcC$WA{eJUMXk<G5xO45@p;VB#i_o@|j@0j>rD#~sDy{twHrhDm4d<BK~yFhxPYs-AH-w6Tt-xrP8>s?z4"
    "y4Ck&pYAx|A}M6uaDgJ*c3(RlGMrqyBC?skHcn*YEg^974gR$yBSY5=Lb)Q|_0Zilg|z9%BEs8vN&*YXq%P1Z>VfkA6*=CPvn?4$"
    "@$45^hh#KJ+>nGutq^!6-wiW=K%ZWH#*i0Z5+t=<B9}@Ktq_RM$l+Gl00#!V3M6;uRf8k}i3H-ROX7EH5Cm|)fd)9Jr-QK6{)wuk"
    "P)PHNooL(3hK6{jQ9Tks^;UU@WqLB=G)EEIhPrzL!qddHi~L5_McQp3{!sXc9bGBHJ-BxIhzDEvNF7}%*aoR4yLIs%;i-7k-oia4"
    "H1eKoV_=|DM!1(a3|}aJ;p9}Cmd4g8>=QH|umhU}tCNUk{;>JuO#VXs9(pK`U&=b?j;{d5fByLG*Z+FOE<W#NN1ev6>F0j|6bQ&m"
    "D!)Y)48{fm3<3nIMgXCLUGafY0T-{x^849tvYr$UNGcTsD(F2~Q}NdXVN>yv(2WRd>)$qF6m+MWil<cYSfkUZge+&s3QX1jRjPZA"
    "!Wr_XlqJPes-uE<w(r5HmDe#qfiPO2CaXLGfeH!)RB*QQ05ww^6|z20K}|fN!k~;n$pR&8DgrgCC_#h@B-I}1mUa1ve8fh?0pe6n"
    "1qCUqQF&VyvdeEV-k@NBnh{Vzj*G`*bf;1nL8YP~JZyurKw*mt4`~Y3xg+Y_hTtLS_yX5lj)WA!#UZ|PIa8P4l2c6WuG3^8$AWkT"
    ";wCi7lx%R_%WN*%Pt<c|8pN42euGAXM8Opent*gg(SD=ojus>;kReA7H;5()IjI(O5Vav8(x6~u0}rP6>6ZIMO&kIKIyp4`ASW#`"
    "mwGYb2C-TQcma8fj$<*3^B*Fw>9!QT*^(f-{r5>gGR{aDpnGe00}AhV1akH0aG)wG6*7!I2ILmZ0Bu+zkYgog2QpNBw(@D9(j*VS"
    "r_88hkSvLkUe34ZT&v;}M1`@|IhOmbH-#70(e`px6(FkWDxvMnv9^c`1jO>j;ib&o6h1v|`R*g&j@LGmwM!*2o)8FN$x(Ev2Kj^?"
    "kU69{N^;dSm*YOtTar@+@LJSCPuLviVl+h+bk><8u!dHBJPFS(f%OFpD2OQ<OqtO*PNGhuMR1jsazWD93mSxXLqa4)pUbj1);y;m"
    "Idqb!OG&!ey8gpVeZe`=-PxSQg;%bhV$B=1_4B7#mMUb#(g|o7=0!*B8v>iiFx89x+GTy#J%|%juI*EZ4Z$EHqdcb?TdIsVC338x"
    "R0J|5N|GqaJ*l|?-KDa{ySC#!Fj3wo!qZKuQxYO72GM~lu+XW@4YvZ4bQnaZAiC$t$3($lBIe?8!@1(5zvXk!8#Tmp*Ar4Gh%Bcf"
    "bq#rgk(>1irZd$^Sv!7AqVc=M^L&4T>0o^>-!3utmPgld=kq&x40s8(=>nJ5HzPhRfA_Y0$2{y$Gy)9<I8`4kK?~`)P0WRDP+1E0"
    "tu>1Ef0+@!Nu!(c!51xch6z7^{Pf2kfBErW|N4(RK9$nzfXc`H|8f6+ouK(lv0^g9fQpHo=Ov|7%t?5@1Cs@&yfj-p3=>T~aY*YJ"
    "_Xdw{TkZ!DaefXJ)1(!GIi@+a^<d1fT9<|}JwL*NUJJU_)V5=38xTxJJQBl8CveQAr)WGKLwQ;YIXWhdc70hud2~$r7<{sHvWZE^"
    "0#%w~fz6X2Vxof4tsa<YVv;E>DrFGfz)0JU&9aW)grOr}5*A?0ImL{g6+T9d9|U9D7QT?5WJ*iw7+(-iR7d6GjgegENrERUqrZQ9"
    "F4>nh*Ym)F$>{&Yf>x(RSYX%O98*Mlo9FakHRsJb^<vgM)OjI4v|vvfZSe=n?P$Hh#Gu}xl-seyP-$_{DtZo9r?xatY%5#R?3x>T"
    "PSg$}=_LniA+V746+L=8cn72F;XF^vt!&mduOB+b@AZ=W22T<#zAQ0%FVT74?F)w}16~U|`Ps{9ChMI!MoP;{Ed+D55zKKXJZQbA"
    "X~8L^+54ZvoPVD7(`S8dw;hyeyOyKn)4AlGwzJ-W?ezt(j`8o#fO?6>FXa@k-^z6THecC!lgEqoo2=7pVv6cNh>vUou@aIw&0j17"
    "X<MTR_3IzKtR>Gnr_P+SObZOm*Ywz!JjI-9iRNipKh={SS>VK~<`mLSgb6}g5&NHFT2Qua8*L|>t%{eyz!WCUn-)-M+=9c>V_S{%"
    "=$K<#I(yQlJfjTS{z~!?%-}gpjK*_x9-w7?eHeJB^b$Q~{R|#kk0I?5#wY{dd6c#@!N~Sjc!`n~aZsfdQU=KP*f9rbZw&*YjV2*&"
    "jycg94uqbJ^c2$qiD}ZZ=s$XXng!mpKre%*Jnvv|eu`*2dd+1~21Su}m>Ag?ippbSq@F{uT1wN~!NW4xXgi{GdW+AS(x&+lwP3e+"
    "J3qY)gfv+?$&{9t(u#_CIwHwB)q8!}>I-?<=j7-@%OELbor%|@+2#o5KzdxgABgzsl+i_RqkQG<RSeB3S|2KHr>LXyyV4GGj9*JD"
    "52WqsfeovZDUH|9z{E#-q}6#dKXcpWC7Pxd6f)OqIXxF;kha=RG0Sb2Co8LsbAd?`gI2e=bSRIG!92<2DJIXMTA;6c*O+-+Cd_tI"
    "TUKWk!y^wtME~byP*!EIRi}G9ahpfqYZfy<S?D<)ww+{_Xjc3b?twJBjb@Qk?tgP?FNtQI>SsNQsfV5^(fs~4j~y!jbzg5s`_eSR"
    "p|=C+N0Jc%JEzIasqJCP+dOj%^wP=yKjPW<=IxY$7CY42Xx{XO%R2q}<ELN#_Lq8SiUriO)4Kl)nn7T)iD^8JY`lAeBRpst$o~FO"
    "FwW%BG1!7b@H7i_jGIc+Euff8dC-K14=<c#sow{<O-z$C#dJMm*%8}9q%|88GZyqZ&m5E5l4}!_$3mnXW}4VGHtX~J01h>Go`5ii"
    "z<3<~?9L&qN5@c}^E)wp(>=%JH!xHhm>56Bv}JT3^n|oNaG99z<&l_VN_&E7tttsUI>uFuTVk?kRXQeAOf)fl!L-Q(h$oYl=mduA"
    "DS`((nM=ncgee=CLn+Zrcs%E6NA~(*u!A_V+v2jQ7~HOhQ#!L=KQPJU;g~|kDiAz2CbJUF1cOJhtn&1urVC7(TEO#jiqT)^!DUUi"
    "2Y9?bg&vAYOq#SnVxlr$4@^=qLCFur$g&RDnMTUMFELJF0QEUq+Z>Y!Cb1TBsyrh<&ceh~u|UU^HKvaccs!sy0@Ha=$fvHJOlgVF"
    "S?3H>rP&zI#)CNq$l=p4j%l-lB4H}6uVcGy2!r%^I=(49662{eG6UgRW2ByDK_VE(FhDSwVZ6XZg2DL-LXV9}V-3g30IecfPIZh&"
    "?t)M;K{(6<u{tn}Cr822OoK4tgUlM)tA}!c=)p%Jz_h@T{LC>2!Z`JqlOrXHF!6i?bC7n84h+RZSfFFPqDS&HOyK3FU^q`CRu_Ts"
    "G(QVWApIwyGVrATyfB4eV6=md37w~|lNbhu1EFJL<7w-EX@S554Ks4uO60PD@Wc~YU}H{f8^?@t`w~wJP!S7y2(NuO<5kQlFp2Z@"
    "(!tU|VA@A8PQ{RUt{>9?A`MK8A0OGYm5st9G2X;*J>Im9VhYDh${HU?(QBdA_EXHE)(_?ZVl{46o|J*ac!W8Kw4hkf$G4VKHu43A"
    "IkfRQ78Qf_I3BQ#2Wf9;{$YC1Y{p6_Gt5a2`tI=@+A%bSNfI-51#M5qFz92r)=!t1leN*49H-JTn8$Hn8gJJK18-p1c)-daA=?gd"
    "7{jZ!C6S-3@bul3Aq`^!=jprgHRceQXj%|eX%S%#(yk-+tM)$UmYB??bqf-y1<rGb(s_vKR?jg-9McG5--t1k2ZdId*Mnn<I1&@Z"
    "?!AnWultox(Gm}`%gIREp|<NNcH+1Uq%S}(gNQJPiJ>_S%v+Q?CgS6ctyF~t2ic=@+p;+H;Z+Rhp?y2x4}!>XD*Q>(X<~GqLyUYX"
    "52=NMJ!VZ>A8AjHVbV?{?Ibxp@nKL>Iv7LC?O>Qhyp!dF?%pUS3e1TD_C!y13g+0vh?*mqL+})>3_1qqr*x0=@j>^tN$8<GnzUp}"
    "ivrU|bBe+JCkaf!-s9{Q+isq~Mx?<L*!V^;WUR`nv@9^k6oWrzwlPuUhho;!yvgIyycJEJ@Bq_h&Knb_n6?Vid4jO*s~Bpvjo~F4"
    "RZM&X(|y?;Q&c^kVbVVl69py{9++ZyZ;T|;^;OImcQRX3M1eU(3@o#`e#Alxo6(b)7fuoxI@kz1cnUt0CE_v%v!IX|e^lenh0Uic"
    "OlH!`2G4;!fZdxxX0tU$=0{?%9=glXEI7mm6DQx72-^<r)PydLo!dC*1uX1Dhs|@Er!&w28+P6$(={ww+3_<nHipKTq_l`yJS`nO"
    "MjZl^7^aYD62|0?iKs779*h}%&Y=?!w8c9VZzK`+YhUhJ{3i*XqUsUS`n==uXSbV}V3v-K$!b|M%)MrM9h&;{kH7!;k6(XW=caP="
    "?)TG2eT@|n#^GK@Fo1Vsm$ZOSMwyr)4P!`Oy7X{qr->;l<`B|!t39%y?<$0C-PhAGen`7LM`}*bHs^5+lIEE-*R77*7$7<Is?~9c"
    "0X3&GKMD^kH;F;?M*Y|rKW%SLv?^YwN3R91wnV?xMrpfd(#DudEU??C6PT!C62gGVLoq>V@e)JMs7)|h|FJPe#S|6eraU{Cu#|>N"
    "CqEoRPSXNe3o@s#noF!DX0=XtFuaBIxk$8w1D|UnBl)S;HZ2{m%nMoVKPTxwYm66tPM?23nPqgI1Mf&h56&h}R!iqFbE;#Uno~VL"
    "u*{EJj!0=?HJCZ&7K}PY5Jj49wNo%V(sZlcw$;UyR>*h&YKekrwT4Lo<A?=bv0&6si@Qo`c1}IZX;RypU82N8H7PfY$!g8fQ4F<o"
    "MUQTQR&G)n@RN@ZFd1WH8y$NYVS%$SBO<_SdyXL%*j69H`z&(W*YRc<$TcjnfUcr}V(LDi`7BU=80PpOHY$3^HwHuxT?wIb?wGRX"
    "!F_@802_Nx6*E?yj<rNuIy%NFqvc_ae1|!P*qC!6%_*Z8iGvWUPc=VOk7M~UF?H=f$1tlE9%o8(D+>(FF|+NdwDC;~?<L4;ZPq-s"
    "(Gv9q+XAIG-g-imH8-gRuxz9C)5j3Ih3KW@HroLo$pw#%G0K{k4rn8V!9!aJ@hE7uK<5WFKL;O23Fh3u@RiU`Er6L*Fk6+MwNYg}"
    "fGNhSW0gIM?P1*B__pqI8za(A>403vBWd28OT0P4+M~aJI4^**`#9g2Ws2F}in%7=;j!mazs*z35*;f$zOPT}exaD_UVD8__q0J>"
    "`}?ic`g~1(PQ5Gkel9F_yEaC%Es4@`V(-jLG^%<Ej^>K}Pu!3OY_tq`*GAUYQDAIo{q%vk2TTG(rN#E$F51h4?ve4xg50C5$t;7Y"
    "ltEB^>jI<b;ce#~J(*wv%jw8ZP^Bf)>ZFvLU*sn#`O)?4*v9>d)B@}=%NwnidjM%m#J*eF-hx@DoF}Q$GO-}47V!Mow$a*-Q>$%h"
    "xc`93lSo7WpS%ugerQgUYIR^%CxLP3+)PlVB~w~9b6UvQ%Uf04kQPmzVD?6y(<uDPI*$`M^`;(s3<=vjwgo$wcci^zb^N9>_}<cq"
    "#JlgzUjHON9FtTG^(WdGt#nqHXqH?0R*W_#CUblfu_=1SMxB3b%&jMz<!19d!%z!AtZtJM@yy+}sE*3XEFG<^lRDGpjdF{t(jn^u"
    "TTfirrs>J%`YoC3ko-W;I;VP^){b~)b5~GAv`^pVgl$YwXQpDF^`LQQZnYl8PHGuYj5b!Sc!J5pS82&Sp|ZoHS#X#+)z2(s^R!7e"
    "^<>lPB5DEm;KN+u7jq0*)#*Qz$E&3?&(E4iTA;_K<|h;6j{kMp)Q`W^LsQi)aUK6^htLXkSX_t6fM9@O0&y3tF<z5)SuocViL{8U"
    "CP(lMjJq+41&;AV?zE8>+#jw^F^7pM4>6u$62WAFIS`K%7^pl><;f<Gw4j)_VGBI}u%qYH<0JSzKL^M3TEHJeWWf_e_*cce!_zuY"
    "Jg1nr<ViSaKzLRdKp1fWl7ZpUbd2Nydf5kcdJ>GyLrSz??Q!s0c!X&mMghuCG%<;MAm^u;z^@~F3)4n0PcZqPhe;>H1QnA7#-W41"
    "f#`AQS}8AhB<4WU1|}hl(=e}=*jpogxyYfGwS#HnE{HN{;}qF+lAE-33<y2=&ST0G(Wk@`QxEgUlSm7Lhm}DbwlPc?wGa=%bC^6?"
    "<q6}1ZUw`o1@ft;#CU|E(){=go!RD@w7jo}NF!HzC>YIxfUlj2$5K!K5U=xKX_50JComadGLcpoCh^kg(vqqtlaCDw>)V-Ju%lxN"
    ">p$ag{=s+(;gOht#vKqBZrPXvt;Oh7To{wT6*Kg>=a_yG0@ibqD`fDfJTBa7<rW@d0DnNCVg}D)V(>M4Qd&0kFw7lhj_6t>#)Gd7"
    "q!!?7_PmLa`O)<hiK(_>4Aqm-Csrz^?-!_T8Lj<$i;tOMMhi&_&%hK_&mIN{CXV@Zff*Jw%pouVVVsINrx<vEDW)Eb8Trw81}3YR"
    "h%m6k975U?Oq%kX!UBv5qUH+SNz`^77^Yt?6VWPwVS<UlJpBSXtS6z%Au1-yu?k7U7|8>wZCsCzp|)i+r&%3CI3}AI(ca`3zkvZh"
    "{}4<dBSkdFYa3%*z<G8thl)uiW=~IifH~OpxYPnS<yl*O2uxgJbPEz6M-@y$dnVh0fc;ew@7gGjh8aAE=KX3H&dHUKz|46hCTKi;"
    "&dMf+@N{p4;OQ99c*tI}kSokUNSk9k!VGDriQ&@vntTJ}xL>Sam4@>pG1QmlmKc~~s9($}UV=<6E|ffTO!L=y6QlFszF=eM?!yb7"
    "w#UF1cVx21z&uIt1eFJtJXy6sNXu?&wbT<>%_aQummw`Of0g6`lSj54jv4-54HJnTr}E$yA5<QvVIm%tf{Iaj`Z_7>W4bhQ(JbNd"
    "_-ZjlT1F$ETk=p0o=<{`3E2BZtd7D0EKOLjjmgNf4FWUe>2<10+vO>W9>5;jIc8jT%`H$c4*A8dIMpWR7!iwj3Z6nRxK$O-(`t_C"
    "DM(M_AupLJJk<*tizY2qNiCie$vcTe&nYndc?2TuK<%2m;H%Wnq4W~R^)Sq#v;#+?R;S4$rJYK<236Xw9?wQGf>C%*lV^_M@lzle"
    ";209|B%XSK8GY{D!gzrRY+mp<ruP^V*~}Cc7(kdHFoCUM$)Q8ye|y3c`SnnOhaAQGGA3a?WPLp>h^Qy(7&329FttQUe4CU3!9??1"
    "Krp4nhnO(sNedo_Fpgi^w<+x%Odyz~ofzmCc>>~9)|u6IQZa%@Ip+Wf1168eBsRK?Ltt6kGj(ZRU~C?Y3FOGqI~Z&=Jq6;K1@s&W"
    "x9!07^GFXUdL)mOmZuoJ!av{T!7Rk-(T$#~dBUS-v=yim7>6*jK<$G)iEWU_x8G^|Fwk|^)Q>;^=|BJTZ}+JwPoIvscewp3KKy_Z"
    "kW2bFPZB&-8rKtWYb6gT1z|x(7l%E;M54!;JmgR_u|VTVrXFcQA{dX4lJXuq4nmWjgry0LA<ecxlU6pR&21|WFvkbG{*aWl#Ng67"
    "NcV#+OyS*+Sg?!HrEv?gY1<CQO)<v@yOxk#yNlnmJ;^1P<y$bgWau+d1z(+uYp&;EZX3xDX=^g4xC{#Z5S@Hb-k)c{m`t955Feqd"
    "JPhN;)rCwNuxm)pHHLlyPp%LkAD|OyPWecF1A`?^cn%Fi%Yb|~f9#bgmZFsC$)o`<Yl<1yi;8xDd87qv43S1!eA&d{-b)_}IZO=i"
    "3z7%x@#NxCB(*-LbC}Y2PRA2G*y>YY4t6C?RCBt)qqam9b1!&Q3^a_|e}XA3?%US;MC2FmP^(3W%39EC`<z;RsF-6~*3yEL_7K)~"
    "3hO^M#_o+l?TvOzEW$S2t^>Jt_fTy+Osn6;9Lru()SR9eL$5um()1Qj%T2||i<Gc5JfGZ)|Fs2TjDLV(wz;LAV+#{hOcAAnF<!kU"
    "W+y)yk6m+tJkGN&gM!BcAuTPeo@3bM98{Wt;TIM?z_6N|Ti_pB;1y}vx+H8;ZppgFXBV?sI@!9MBkPx%$o$~zkFsf7HglR6wrLlB"
    "CG!$0o5#G0C6nuD@bw_Mm^|iHEZMw@WeWpK3+8&BTA=3#-p5>0vwFSG*DP=!qz@TAi&|joam#l7v<yIPRo=7!W4ww1feG>x!E9bL"
    "o6`df9hC$7oLOM-=ZiU7m)lHuf_jNg?lWLeFg8z6t)5Hs>QyXrOn8IG#=r)KeSlmsybKbTMsf<g44VHEUFhyV*b`G^ygmevf?-$B"
    "=@?y_R;SLaIj7DtnUs!yC@q-MY#u+w_=h~8Tp@50p5sAIw=5V>d~9I$^#IQglLm?&P}d<@ZSg?X%F0Dth{w(J5FW4ER``{d<AIrJ"
    "e)JM8{8~vOO}ARjkCIca$E$jDf1=Ef+qT*f|MfA|Q$!2VZF35bQ+;U?qt=hGO_x@L|4p|5Ki#AI56aZGL(S>D3<~icA4?wHZ@DgO"
    ")e~&+oKyekIzNkYoA@oyEgl_%z5C~v+8c`(D0&L{zU)+@FS{1#aSR)y=9ISqLt1_lLn2+Igwh_ymS)GMM2|eJ@lC-LHKHal-YRQ5"
    "KG(m>KD5ztf`NxTz)DnKzh#2q?Jb(MAfw9#JuIikPs2uJ)hQ8NJGLw1+j)wKDn>{f7cYtXPaLXg63HjgNZV?!V)8PMULHi)<I=Wc"
    "p~tf_&|~k(loq+w<dlI|ZL>>sZkt!@C#smWZB!4i61B@($M^@BEHGg^KYnU;5z^9w{J=J*ETn}G`kW@kc!nv0Cz2i<(c?Xlv{6mZ"
    "{k@OEvLj6A318%)9m}>LGM@C1M=u=RHd$;xfBf{vKmGdKpZ@26{`T9rZi+kCNa(z8);tLuFn1W@;h3Pg_U<!cCePO~_?G`DZe0fx"
    "<Cd7P!4sw!<O<43@JI)%jbZOPC_J_vih&PtKiY)H)>9r}Kw#!hW<5Wi)%Fes-jD{YKkQ(fDh-r2nzYa#Yda>Uhr4LI26o&4tV06d"
    "h?(n|=O;YCfWYt)4Ql<sKM~{2k#7gX-;?p`8%Y}&Tbd|m;4U3%qbbdqeZiT1fqdd)VEht8^t2CoWPUmi@ca-A$<L+*PFMh@1$@o|"
    "?ZqX=gE5}ewmJt3o;e2aCSSoEGmLnBOXdg6GJrSBV8`lH8F!raY8%DqJa+4qcA2jY$zB3WJ$j#8_eT1v5lp4gmyopaz>D!f9YcEE"
    "dVDCwz;HdDkMYW?6P7$q<1sLN?47S}gF0`6IsfePIFrYjvzaKn2N+mlz?`@B8N->gjI)k9O{})d;N5bI=G$y>!LuiAclTkh`M_K!"
    "YI?Fc9%OS4&ZeGhmUY>{@OEv#LTA5_r@!yGBW)i8!U9x6#T?@&7_iEqfMr_&tHl?vdP#BC8<$_OS{bW~xlSxzJN&|U*y^bS6XWs6"
    "rwdFSm6;yhYF&>ql20(^Ok2F!cFb9`z($F3JsZ;KSp8-@P+QgO_u|YK4DDAO&%GAEiSe5lc&3NXSra{A9ivyIfvE@hNWtgR;;fmr"
    "m~(J()?7c4X7c3IoY6Nh8)JO?G2aT-G3aQWHlG$#PchqQS=hF%haDz`H>`$j3m#(RL09EirjsumD=UXJCT(EcHb$(T^bZDX9x_&i"
    "4NvgWThv>=I-9YN&tQrn>ughxH*FK+oBo-dq6d_{CYV<5VA!!LiBa~nVf6~?T$*lyA&tyi=KI_`7;o<Q`SGpOsyQl+epVr*kynJ%"
    "{PkEcE#SxAPOIFutOoPN=4npfDr=aQ&N*v4x}G`DcIo(OPGOawMd=*sTeRo5=mE3!E^}(vw(%yhd{rEF+S?psyy-38ohOIbO`aWT"
    "X;06Ik4JF}D25zCIW^xc<5A0v`^oi@k7BTA+vp`=j+S7K2VbnycSaX|<g>@Bfzjd%Pe(o-GwOH4YCHC^#t_fkCPv0FR4=tEjbg}3"
    "QefuZeHrBe)oSr^j~cOYB4Xq5{9y99Z^JyXZ7$83rSl{@24-z<_25UX7nX4h+k$EA!|rpEN9l8Z#j~4JyA~dl&PLx>SL>T`COX^f"
    "&6<M8DW7htu`#J-gXb`L$_!)7vxT=0!vdJC0c_ihIaBVxe*XCB&wu;tAOH5(*P$u@`${c*q!0J;`!Dd?aNm$9ATJtkL%dD%l9P1^"
    ";i8ZiO)?>#a)F=$EV)5^&sWrG9F`LWBoK(NG;ng78xku`AT$`_JC`RA-yjF(k`N$}fFPdI6v0(6&8xXU#&Q~@Tli|Zkc5~lR3%|@"
    "5*bZc)dh*7coLQzDvgA&stBSgBGzum2^bPh2(!=&T^A&y<^x_>_y`g<Ag%EN=@u(U*nsGAvJL^>m2XH!0}16ib|Iv5pFHp0aV`%$"
    "UpGw<5F!V7y?ZaX1|(OSz}toof=jeRFIumUyv^Sb+y#B&9oJ{xxo^mUxdx=!eDDG3g1iQ{!FBW@v(cP<=ncS!=Np1^+G!$%ga(O-"
    "Yd}1KytuBxIANL#k_Dt-u0$X&nrpf^Fyxx7P8|{}<dyf(+aZQ@uJ~$E!DGlPUm+klHw5Q2zH%CHzGBiL8EKENT!exlFPp=GAxDJ_"
    "IhV~ir`OfT5)yH~uB&t-&ewG`KH?g@&S^(nU)M?}Vw<l$MZ`8=Ug7}>)u$bC$zOi<>vg`)_0paI>AE5aDPYMj?I|J16^BZ=<gdtX"
    "!nr81O78aDG+6r;Yl{ccUOdm&6{U&^(?EqV8r&}~o1@3MD5Q1*f()8OT0$$sfcwSe^$(Gk{D6d7I{|CIYA`rnryl41^7xVdb+rxB"
    "D{lxcjqA$NF#=2=#2z3^wgv%Q8dnR4lec*g{Q^Ya0nxw6D&?lZC3e%`^+rr&PI<|Rb^hx4x*>Q`8DF(SG65J6>KL&}ku{+vU}8wK"
    "^%NO|IiyYfo<h8!@uGO~G<sJYo=UD8=}8qN;MH^uUu25x5JrR7(Mhc08Km7Y>+zB%Wimy!Z+SdkLNG}0G9+JT?I5Ewy4s0o_w;z8"
    "zq+u;xwyKy$9sr-D8Lrp!v(Id8-knhJ;>li@-@H)ys*CptAH)M2DE@nzIZZNNl2(eZp4d<lE^UFA$Vz24l<l}2;TRUvqCz}0d+9%"
    "G>0Ptey73pb+n0N(7bYya@$RIuEOm}#O5L(*K|X28mc|C4CBd5{?2JcwKJw#Uu!Vpt=Tnck}|xf+Q3^>3|KPM#lWDsrY&5C>EyMX"
    "+QP$=zC$6AOk3@xosfCYy<1(i=j!hP=i(X@NL#%ZIb<X`DrC@PGTC9sph>;&RPERJ81U{tiXIn7uWVdUA%n(o$hDZf`+McOm!P;b"
    "ZU}Dk9WrRLfFv^7__j!v5L_A^GH5*am)sC_JJ3svZ4f9;gSaj^;*CZSTMq&`x@4QH=ny>b_-t~~EfuB7JQrU0oILe8wGAER68<C~"
    "$wo|vfY`nP_a`w(-^?C@>kyKO_vq|Pqlh=)WE1LiND`a$ENJpWIk!U~2^Ya8ggGdPBdF+*Bp|}~Nx2T;bZT6EQF=R7@NyUEVloP+"
    "Q$((qC}^T^;LPMiAt&gPrPJv>IVx8WHe1>!a%A3vusLdwIH5^8O%igF(4K^xB<ej2Ik|0kJ693)UWDW#Bp2>qzae!i4cVk&?eGu~"
    "y!%)}dYdPZLr9j8B0TN`5>1-syo!_t1dYdXjs=akX+YQ$`4~l`D2IrC9Gy#-6Vxcm_0juZ{_)p;{pC+r^yXFeALRqOr#9Vgz5$4D"
    "0jN-&rEr!;5jo2qAYd7RQ>cKjr04+9SUjij8b#m~B>S+G0bB-5DOx;61BB+nr4*pBoP%Q!V9QTdUI&wSGJ%JZjte}N$LR~BFRUP^"
    "_}5m%#`}iv?Gno?gFi0Pm0rrj^jaDw_$nWDBtOO1{3Jbp91ko%z~piJd-|*V`5t}<e@%OoCibi8N?+J;_QGdY-wBnMmge*s={s85"
    "(05?|+8;8K|H2oP|C7n*^j8NgtcPaa$;%V~7|;frf|Oo>qiJOnKq>GzIR``xfI8-%d{!W8Gp9fRe^C@pQL007Wai*JXZKk)CJeb~"
    "?mYvhxgmh$+<PHF${7S&h|Xgg9O8u$qVt$539gJnhBwXFMKqeRi+GLiP<OL{hYvpj@D&nV-=9>;!3!GScUg@l^j%h?iG-$k4FET^"
    "fP;w8y$=*}^gU;ToPDiUA<^|+af5grg3CFMopXbvz9(;x-2EC2GW;VAa&pM!Kk~T55_HLJ;2Rc7NE>`T&wBz?hJN_3d#Q%z;}#Y|"
    "5D<^F$D_B^I&|F-$Mb$7<rm<<y2*IjT={(fZU8(Z-7Ybd>jr=><Ekhu6ajp%%3hW&>hKAe2Sa@KvweD;9p53%xIiGCCI~K4x`99_"
    "4VTlWvZWkuGp8Yvz0mIOBGvNlQTYIo?6@k&%TyFHu}-bJ$opI}0j<Rp-YJXGE=MywIRzP;@77J~=s-s-radY1zD`E01ZuBsQ6AaX"
    "hhLhEJqh^OlU(=TX5^QqqfsGTL5yL&{{&G_UK=k*Hv}=Jy6#1+G<|FykRrx!3TX!_=%}CgsHV&?fpE1$Ae0LPSMw0|e0f@@?U)MS"
    "Wu$LjyTO&oT-p!P;8N|7!4-I`>ySa?>(~sfN28-hnL#=ioSddZx}1I#YH%H-UvwV}V6L`=f;NWVo*CE1lkPiGA${bB8u%T`BVvMa"
    "-i@e|5YNSQK%)Q+aG)XkS_2<AkB+l&igToWOBa;iqv5Mn2csto`*?2*IDbL(1&?u|Z!|c*+m{=@%FBa(j<50)md`gv8}d`zn6-6@"
    "B0r&7%ETv@ZllkTkJDoo#v4V9F9Xjvrew{==B0%7dEK6<+tcljEPrtqujn^6{yILG8*9m*n4=?&`kwI@rf-TLjvJWaBkMn5fsfKN"
    "MK;b6wYP2hJo-D<#~oYE^93A0x8_*H1;A~jx%tMR3CwCtF#rjz<eKjgxc?C}8Dj*Ed<4Z_m21>ZCPly$7!dhb9#slFAw)hQ=rS-x"
    ";xh2KGohFQNQot04T-bx;ST$_1;y}H2pObaG8-c$MPlwK$OZ*yG8l_$Y0$j!+$(5$^s$VeKYsedkAM5+k3ar+-J|O-)++{b?>+oI"
    "5yA(w^b7s_FOH;NOObnvLkYsA`3h|?g4eJ?054br00%S{8vquC=M+e7Q0!=c$XOz?6u9ZYO@|>PP{3RUQtR$CuynUmO(z8p3}4eg"
    "=p*J2ro2h|6D$I3KvvS53OGI3>8t-4c+ly?-R3oU0j0~XelE}Bw5rcr_6CLz8hw`!O@6TT^ZccS{Ac+I%lsv2j~DvGZg~a7pPGKZ"
    "tY6Nrwx2Zk)%IYPuV3b$^V9w#+plMMZ_x+R!Gqpjr9P+8r-gm7(R-nf4p5#ANPUV33?Ik<)JJMhMp*&~oT7^`C_Iwkxt2Qh1v)`^"
    "B*WisxNi6W)SP_=0tg7;ImHy<MrrnR(-D<4C~3c$z8vdnIy^{6k`4@y)Axdfr=x<8lXUFq!tgwO9n3}acY5d__@LrX#(zighWr||"
    "ixjY?C`e}oP^CxXfbR2PBF-rQZubl$sgN+l0tg!5s#TgaXsXXE(HvC>wueAgG%%xy76fs{4X!jwLu!YXcOYCK<N(flEqN~4VGBDK"
    "5SyLIJBa!sl69_=3qBFW-ME+x1rSMdEG(Vdm;<QE15(k~l+d>5o^-N!Em<($^|XZthNo%Q_1`WEo`#+-41am%MH+gM<%*xBfzgA&"
    "+w`fYLr*(Y9(Ni<`jvk-$U&fQ@$sHyRKU$qry<vCC^QOBDTd8;ejJ&qfh)#>i?IU$%Ls_Yll`Lxs8jnW8(<V<3+meP!qH^I0#3FK"
    "Z)l5e`0yIuV0VKWbEm;g(vBy?NTyDmDRu4{fks`=A!@1ywI7>`gp-vzD5^@Q4yqx<>{2t0k^-xUvWW$@Sy^fU>7vV~Xum`3B{rGK"
    "dwmb8sFC4_v9M!v=EPnT#dtw2XeD_MAOSZXpgTyXCQI$ax{;>MNUvo^siQ&9ps%7LHlrs2C!19y*+pfZWF_e*wV$h1u*h$u#1ZeE"
    "Si!E!S>qK+kjcQy8DZ}v*+Dukc>^1%8Etb%ut^dVmz(?OL;JmbA!8{RL#ryvPKIk$gRqGb+ew&U{W2L$EYyuUN_v^Rch#=5$`s-p"
    "$oK~GQS$pF)p7|q=fDdh&_awO8EA4y{`upl|M>N{|M<s$ygb`*)R?ZjmkBkU`nmz`WiJ7|D6$H0BVFoJ;!65y5<U)z1&Y;@<sv3Y"
    "fh{swKl>`x$oe&Oy0CQtQ`1LJ=PG;P?>vrlA^e%)QQBj9_vits=Oi?&r&yp^FtL#)eKo8mfhSv4#gRN(($OUJBD0cyB;A!fXtHc2"
    "kIs4@o;q5|#%mAtAelz3G;D3CDsLxF9h+(LI@A!mRb7-wo-_$Be-uq$cz;y`BEL@!6U`m#k<}y_Mlw<2K$HGT_8f=X4xa9sF~07<"
    "2;SfMDi(dH>YSRYycl_4<VeOQ_xA=ll2=_`S-z4dO(HCy<cjzFxXb81A%at-kq#tWa?(JyWUjgKB-PqvS2-%IA@d6fG&!(ci|5$T"
    "ur+i#h}#I4C~+E!LMs-yBnL`-hucpy&c>m~8_9a;-ADpTo+vdMh--~&B*PH&$t2<Q(b9>fQN<6umUj1!y1d#=<@a}C_jDNevP`?%"
    "mvG$eu&2+OSrEy3_N<k~XWmceo`#VwdirSTW8e!*A3g1QGZpmpq+TCcs>dyi`unU$xO)~)LVy6hh?;-07P>=Hdoe@3{RDA=4oMcx"
    "(Z4=}q(MfL8(ghX)l2$NGxCV*=-<~-$#n)tl0AZO8c?_>1iG9+ath;1+N#|VNRv!yI0VTl7UY&(&%7d=V}~@!2|)^hXp*^{0kP#U"
    "2r1{NTX^WY2-l&@kv6+!4c?Obg^68`7j46nwgIe`2c)*TvyC>5<fIgFbUzHZh5*u*Gi%*YA<#N80Z5V#@uQ0lCdWxmCYGdqA6_no"
    ")CubBkoths0iFZKkW~R~K(YY20~{MQ9pWf`)V7kxy&h=EGV+*YvaL-?GPPu?#EvGR9pyY*y|HA_lB1S=opr0|(31%#YYBLi?7XPO"
    "j5!;nTO)LR^_lusb5xKU$>Gz6yUvGC`>u_VhAz)x^19zc++4it%qkkomegaV(wr`JDVuN-IjA}DiM+94G$<>1e|8Z``Grx|scxF;"
    "T0G(;atepe8>t>8i6kdg5g;t8#nkI4wH*a2H=Jy&XNwU|XzAWVF)HIE)Z|H!XLWvLnpsKOiV0Y%U`DFrM*7}gZ_<NM7KO4Yyw_nK"
    "@ns^V;o{YgWa^H_H%ggm1IwK%J#`OBh2YA?7nZ4`N};J+rj^QdXHQeUr_SrQ*SUn!Q>msdPsBjhWLhNe-4_5&-jU#3+iOjxYDC8("
    "V(7{9YD7p<taXl@C(Xs(1taWm2zR3hHr0(?71goT+=lg?xPE>^B!|xHM>66hB91-jhwmui<Oro{#7eRfr)nhezBSkE?@O9QlLTA7"
    "luXEnTCuUsF(Ya7CWH6jqLOX~B2EVJ99zDCJ$l=)urMi{RBIn-ev!xXCjR;3r$7GVm%m*e<ool@JB)Bg%_|^wz&*rYya;ed0Bisd"
    "836&pBS6|?@!WLac5DK|b3m8T&-N+ld;9~2H`1;qJwtmHy+IvX(o5#svaF#;GEh}P!M3FT=*J*#Y*LafOw_TDlP^HV*v(|XN#IGp"
    "Oa{ywsVI?r{gi8A6)XCv#~XPn)D$pWybHKXiG**YfN6+GrlgDr7ptYEO9><uiFS^QHAV9fO?}i(n(`{;y-fK$x@nj+RMJ$_2g*bw"
    "DJ@H0!QoUy1(Qrle`ycBD4KSvA#bI;NF_ws;sDK-d->leV?U|d_`*j*Qi3X_g&OV<xF<3P?v@fz%2$W+eXP#c?GeX~6vySN54seb"
    "y7i4z=&4L_x#sr%zHOcgBITR+xEVu|^_+F4NdsFaC6-L}hL(;kl=waqTc^!ZlfJnaNHXi#df2X9fh6DVg%ZhPVA~ErB>NRXcRb7E"
    "<crw#W0aklr%#zY8TZM!W%?BOSowkBf${73k@n3;gaM7fa{|u@V0<916CerTI;68iOG(%R00P7Yhzkm2NW>(-0e*ZUZvbEmkft&i"
    "05;Sjz_C?i;|8dcrG@3V@r3RWBvpM(tNI*0XPWl?UVx*G4mEv#cyy;8#^b)_Y2R9)`;7p7{5UAKpiWPSLBSSeR~Vy<AD?2EI>^nF"
    "aSUUAd?t@X#XjcUADh&{wS72(M#R`+d?a~~@j#QeOG+jYFHJf*;_pl>QAx#~8WUNld}AWRQ{GLP*mRiH>Cls@(vxYFrUH>7ae*x_"
    "nk{rG5Yd7nqQwU18w-&r79uni5v7I0d}Fmp7gKn_G;mQYyD(quxVBQZ7jI+5i&w*e;rNQ)PDKTG#V`7HgHoP~6wgw4IqD~ruV?ox"
    "tW#2Be*u$}pQJdS?;1YugOYag-YBK30NTd`cdFAS$||rYKJ}lu;A3oKMUoMtq{n(^y#Ax^H);CS`^uwqM(JC7evpnW9rn^DznZ@7"
    "jU>M{9T>i+qezFHv>$0t(%cmiAEna<J(%=S;5B;a?kY;}nct}O9f#=CN1*<$^fA5&9nL&YSiHjGk#|oQN{c0Mq3r|Eh*$!lh}<)W"
    ")Hc6>R2v>>VID$C5s}&{g%BEP0lh&Hk=nSExj-z9oWl0YdMcy3a)18#=}*7?;nzQ3=Y-FXE8gMS2_s)OCHJj+pY^))O4A`nCmL*L"
    "+rRbnYrR$@+gCc>YI-`7G`JeJMHJTwM=Ij8fA<CX<Nn&O9=(Ee?ExK2*PPU=?lnmLc(FoW;kk5wOWh$SgZNuc=%18b2d_BfT+-a7"
    "aOW`~k^ykd;uXca0B-`WVremXcP)Ge;Jnk&IL>R`h|?5*2>Nng3Sg$MNSk1g=^DE~?`ng7jG%Bpz5uSL)1627X23bxlgZL*w3$`Y"
    "t_ncO%#(+j^i9^u3!wr00K^9HSOEk0{tf=<Mxh-wDeYUy8{m5$>&WMOucClKk$XA$M#1cWZigQ-2!-!8?Ay5&2Jo%QkrGb{&i4If"
    "I~a3~Y!1on<6(tdrv>92k~SdmZsLxTB-Au2z>TH?_mLi&uJv7yv-&Z@bx6XH-=*dzwNivZQO^?j-c{<s;ZTp1wH>wwh*(Iu#SW6+"
    "Cym(jR)W|GVgp13_+4!p6`E!c*RM!OUCIE|5M;mmoB?7t6;lKX7((xB51~drG0O$$7rP-qy>|`TtV|(@CJ8PHA-Ycvs8=dnWeelr"
    "?tl!ZQY-&);X3%bd>J%BK;nSZp?V2<xfm-57$|d4tKjy=P6MGgqc=hKmf{n=nA1RhJVa!H@*L#5^$Hb?cb9M;>sy<U+E*j}<)w=%"
    "QBbl#u0iq*smHUA87SS~xb$bPuJ6C94fUO?20{;1U5prX+~RLWMAZtyLkGR)rcd<L76y4q<tbHQpz{XR=j5+bDTfJ)QdXnNlIrEt"
    "D-`rP6tMuEAJ<8WYJH#}PE`igYo&`ok%EE*ajHx~Wz<m9h(MuJDU1U20wgLc_g-aDy+G*(0n&JCpwec*fMg-it+DX(N))6}y+ALj"
    "Ov@fsEvCYtgUA|9?jWE-Kp?4FyN?ottalRBsPb(+r@~z{-x@L10C6fj0wfibZ&1ILd4N2lI?yN-Z&`P{N1#GL;cgRIf)WDxyVuq|"
    "(Et?!g4eKG+Wl7bI3K2Jpm2ly2rq%Ju7>`S2Zr3C9S9V12uLB2FqTYVKvWt(XuRO6OEEu+sY7nBOur?yLR`NkwO+dO87K)brrg9h"
    "6%w$j(*RVjL5%?Wd)YUxvhkSZ_7u0J;{X5w_}h@rv2^ldiQ2EB!VpQ5o8XL=WH8pgn51uAGPkCmFeVGiP(2aDB@pVm-1miP=qq&s"
    "iA)X*$%t#Lhy%8!AHr_Swm<;B1DqivbS;j^2$-dBX)*$MY*+_mv=af$(gB#IQlP!3Ydj96$?g<x7Z3EK{%56csq38S2O(`qXfMcs"
    "K|5023|9|-4^mG^eRom;-d;9)`Z(Luh34j{U+T24BxoA?^rrw^Jy0I8@4$240S36b;SERyPsbXM#p&=dTn%@O2d5nJECjsMJPEQn"
    "@0^O$Qq7G-(xoO_Bhu5O8TPawusBYt@N8}ennvUYb5r$V@ZHJ8lF)o&$4HvQRCKCuAW`bT+*=*cTs^U;UGoB84!R`L#OcQXfIMoE"
    "17;M%!|JOM^ECFi`XQlvQWJJ9V?g)EMhv(YJVQi6UXf0Kb>!L+Tl!!E?sWG&!+8w~&`w|BH1bRbl1?LC=>v0Idy%H{aJpX6Fa%bB"
    "!yfrO-0hO$s5YA%$1o~4qYGy!cP=o1a-fG7dNH->n3>?cNTVsFU<p`5YU!Upe)_L}{Q1X!|K-PDfBo+tzr3Osb+uo=2fN3c+r2(6"
    "nQxHsg2sSE{PNr<P&o`z?yhqIPR{cT;3&Y~fP=Ff$PS%F722}*2?$b`eGSqVGeXf7IjU>0=6j_O#sz|_L4pP8enUYLRFd1hc8@CK"
    "*%5`{T8s&fzNWl;JbAd`)v^Y_Y3X96gP!gm(;Mm2!h41XJ$-%uXcFB1z6NmwQZ^x74h$N21M=A{mJp91Fd(@>ZkJ$t<Kwei)In|#"
    "VM&ayMj#;&NsiGtMkBd=(;vE(gNQ>Sf^;@4`vOH|Qsd($#TnZmY6YMfpozW&C6V2@fK;}j?be?Z{T@MvwjvE6d<s!)EqT<gW`XBT"
    "Ak9o@Z6FgqDT(C8bwFSweF(BiA|?Tir;mIJz%40Emb#HA6i`2muKl1vT<;lcn$S<C0^tH72ZS690R-t|PCtg*M~@yw=#c&j7ZGGZ"
    "i0DX1$_dE#0k`>&C?w-SeF_-kE0j8uT$lSQ5U)ZGG{c?!f!GE)CXhB!mJTVkM;!fG*#;>H;s(S!1i3E>00UB2`X8RrNJ#F_(;l5`"
    "Krk1E#11*p^iBcYnOs|97*E<dOjCC>O>hUfzO?Ai+=2x86;+m04CKZOxow3cs63{^vIxizP?Vq^&c6OXFzDW_9y6*gi-GoJ8H^_e"
    "5ys~2P+@Mo7d)}7gQ8T>PhO0-hm*~SK#A0mMWtv&>t6)hsW*$tGf+EIAk836rLVC;Z&6utW?Y$bP(M}?$?MR7dRJCpq%V<v`H4q`"
    "q`<~YjVjEyF(z!ldZ5Rq>!YD3urZGHfg|_9?xdUw$Wah<5E{n~$k8Ef)Yc$iLRu`Ska@*|0GqKSB*}@6fwBbxJVAFVPv+i4r*Q=o"
    ">)rSkXnX<`$bN!?LVsHhQ3+7!ixLCWmwf;T5;}zL4JarQ(2#UHi9gZGRO53LRNo0~<LAA`h5PNBlL$KpjPoKZ4l0a8q5|=B0~^OW"
    "72CuheSs`#94B#nmHjDJ?^tdoQaqK?DL!eDZHUSJH3C}<2L-e-1x7SCC^v)1zR>Z#qX6{ziGw(mA_#<Xw*l$fHnqfXw!qHTC(!LK"
    "g_v3IQW9x_emqU#R6T*{A)ELnHeiQ|(*Pa=h-+d1kQ-(WAp4<0wmRJbbX)3FKpBAZ13mRICFp6Y^U%`ANOz~0XLzsUOY6FoKQsA-"
    "$<J&|$wQu+PHlYi%nNw?bcdJFw>?83={TN$rFbLV{h>V_WcoxCgGfi>bVSd+I_lgdfc~H@71?@NGyt*tkOO`*wtl9BAyi7BO!f6J"
    "3W*wI$%P>GrP%7|pF-|e-0+jMjHW?`>tCgb7MGM98JFMS@<Nw4EUW<xMw8#AVR^T?f+9JZ;gcab(GWx<`T66gA3y%}mp}dWx>%^Z"
    "hLdugAxigy6Ic2L$wvB^;qxnfQ?&FU@OL^Pd9R;@@Hl;__7x$I+Q;Q#{$t92V*XBl5P6cn5c@Kbhx94(4@Q3|`ZMBh^oh}DqMw!@"
    "t&d~y_cWG&kn$^49<I+U?4RS4h0l_o=qozCl$WRWBql$J{N=9i{#J#SM<V$-nEd;!ZX)Tq{w(atD19(`nT|+b!TQU{UpCStKgj;9"
    "*{{k&`pd%JUjIh<B6@0n7WKvLr}FaDUW_OCJqCSY`b)<j*CFnfK5)9y#|eF5^arCqX7q<9AKBaav#IaqujzBtUrQe%e??6nn*39y"
    "2|bce(^CIo@E42+w*pj)LrZ5SF%FGq{T}(gIHT0B-HAbdaM#DzTk<|=+KF$kcTaxSmleD0&w3YRr8w#ys0@Ma*hM%0ULymdxEvZj"
    "V#pO6$xY8uT{fPWa;*?OqPd)3At9Q}xfbedbD4K}2&2PX2ZCH&0V?EdG$C}FYGLr5rreS*NWdBGTo%nSl{2&tt^;YOG=Ly`axfRQ"
    "=jLj;00QYWhky_o%oPdOUGit6Ik3&3%Q>(d5ZbqCN-K?1aGhV1eAtp-G;S)HTS&NysO8eQP66S%qA2H}K&Y;wK;kpW(!yg7X}S(2"
    "7YC*x+IJwdR41*jL-e-cbekolx8Bznu84M|qn<3QNd0LyO|H!1q6VF;!w;@80G(p^<B*6lc5<T!5r!O-%&)k*vOOZ;1v^IVlh9Pi"
    "6`zZMXs#K86yp{02^rH|xetiuo{a$I^@>jTTCLZ!3w2scnCP1N0y6sctz)B)`=sO0RZpCvY}M%75R0bi>j{M`Dl-bJ&+_F?-%llt"
    "bZKjZN`K-d#P8yuFEI)N#I`DKfW8cFfTOKb8{p(JK&Ux6Pb1N#IJCY>7;tbv;VcKYwdh(7OUuEv9H>Mb6M9-4g>$s>I5i1{t0)=)"
    "P2U=hCk&d+2ePQBdE)#B+58-Ly5e)gbNasd#r#Nr9{LWH!A$tM{@Yn_kj<+>&+W_1o-*vQ>3RO7zAWrJ@6CjgZq5=+Uy%OeiGGxy"
    "g6K<27fnCKAHv>p;jQ{>&a=XtKV1Hy$uCU5Nq<c3eUd)0{4Vb>?Ky?K!t5<feqsEmd{p{dK6OrVXWPk~b0>3Np3Ip??Kzme2g<K>"
    "PTqeqaZbwoW=(!~mU29Iu2TCCR$d2l)*gcX5c$iKbP@SEgnsN?()6k6BGX!awem~`{bBGYBR|Iie{SJzXY{csKSFQHdpRe5{`lz+"
    "fBNmuzg~WQfcvQ3xV7{v5LnW9g9ZqVE*V`o@p<1`g&}uLlG9Mh1LBcnXGq@Wau$~x?|Bg}J6~SOmo3N6yCp}LT)*<Ga-5LtSna&4"
    "t3y17z=CFCPd&hB(a7=vp?$}~0SO8X%(z0MapP_jo-dDSq@2)m+H^^X@23U1cIbB&2NS|93_=%?Y|um<5==-$Ty8+pT+X185L-@t"
    "M-g!)At!YjuRt7wG_G8|vl_&2&@@Q>`VMi~5WnI&8^pCsAx^C8s2k$JbrP-y@vd>X1_31JI?(6=^@1CMTjsT|_a4dV5Kn1>;KFUy"
    "H;;C2s~s}9nlnH`JcVRbKG!i-k8Amc6jaWa2g4s&d#T>@p-V!J3h@LI0Ly7!j?Q&^bZ{Al<{R;CzPKT{G;UvTLgU8eD-RiI53zdg"
    "hU8S8V0Zc@r}=6ISE)Xq0XeFNXFx8W4<1S4<rj*G=7waHi+FkJ4@`3%{lwbibz~H4k411@_LMeLyGDca9y779NshQ3-u8g7*`YN+"
    "Y<^W*8nm2Ct&7femue7oQMLO~UwHj<)hTH|SKDaq(D&2uKJzx#+Wh!9!3Si|-NHT6)ouksT)vJ8eHGWPz4;8C#vurNpetxT?=-qd"
    "2F;Zi;`_m1y7r5GP2$lr07p~aPVII;=+~hkihfwgkBjspvi4{Pmny!DbiV-KBMtW<z>&URSv1n^W>-K0+fB!vLjc<Kxv{YT0`yz!"
    "KcfnOem(tX;sglbh=kbF0jJX~5ZXIdCjTlOrG+e08lc?)ok+oSKz%fzeSpvb4yEIr?hN<mVI!SzI^DG!5dQw6>-tCme=2>aQ~#Ly"
    "zC9xKFT1<E`i#R6cz>YhaJJh9V$ih3-4GLNcj=0u-hzuD^_DsWsh7<S^P#!DJI&pFPY&@8Lwp@71|-zsq+8gh*#XIQSQ?P#yifHK"
    "@-aPjntSSVh~}Q?s`l&ty?dg=dG8b5O_SQRRxl*jiEhYg)7sG90v8=}4fZi0d-}AN>YeiyQZU4E$SpZxNFkDQwJ`d-ZQPKAEW9DH"
    "PR;`oYQ6@S@1+qc#C3?rkc7DIg-Oj<9FTw^rPf7klCNnb0G5+b4c=U_)^dH^p+Sx&ryVNrxWw*OS8mBS7t|Itv_o%op&m|f6*9P7"
    "T_kp{dl?%M*9{4X>s}yxWb+LH%vCDn=Aw|sRd3a<kU}6$S0XeG0w?CG_ZcFt0cl);K+1Ru9dU&YX*8ja5{;%lbB?$MB%tFZ3Rl83"
    "Kp>cAaMh<wIakD7(8s#Q<@$IS7$hn*t#(`=R|%I#TqhcO4W`rL>0RLF0nP&`2My4L9Ec*=EWKZ)0kCBpghc?DjKH-p88Bp=Xh1v&"
    "M^cn%948uxQCe!q?J;+1(#dl51Yc(O#Q0NtB1y&f^a_8rdP-A$VPOx|2TVTf*>h?&cD6=<YA`Yly2L02oJyK#JWY*OtFlBIfVc#_"
    "A%jt9E4suWLrUEQ5C9bmh^3Dqak6w2iU`+K4ve)vhXfS@M9!S1Z+5!3bxC9Df;T09C7SW`$4|ff_{$&u@!P*$5t4u-8*M2b=stBq"
    "gFT&$D>h#~=JM2w8L+>f$^oGr#+})mE8rN#&;<g*ZT6d7YY3<iCoFV!-XCdq3th0J(d4Wly5vt@tcz^KjbeRFlcrqLir<kVA!!at"
    "yOK@!z7x)T3h~0>?-efMsPB@U2nwtqL2w0C4h{hfd$LKRhZ3AYQ+6Q-mLmfPGPt0J5*oxYh&RIxQqC;g(8|XMKzJ=A0nbAcxEFXY"
    "LJ}j~5Co*r1QdX94AMR#l{5*ta4AF&Nx0$EEvT*bAO(mZ#Ry~^YLFse2m2k8!1d)%<gC8K1WrI&kYWTEJPA_hkmkGTxd;)t({D&3"
    "E_WQH0P1o-H-Z${=G#*fQ4m=PTX+#l2-UyC!WIV)HzXX4zCseox2gICx$b_#y3*yZ#_cfq%Ecf!gmiI@ph=Uggh)v6C0C!+fTZe^"
    "8WzS{hJl7`9BQl4iIP7>eH|z`h3X40W$s#*ArcU+1&3ouK;#ZmoV8yB8W6#Gzxzc*i?+Leg%-BxfkM1AY%d!i$<PC`)!|P<BxC%6"
    "jH42VSPsg7NG1mZ&=b$-2#pycp(kiaL<9k#MMM%>NB0N`jMs#5@S)fd5oi$*yqb^0Cl4qc@Wbh!cw^B5B7ODmd4!~e3c8IrAOc#1"
    "M2|<L!GQxFI3Us(Kns}gfC!h@ebhmxkHhP41!R(pmtcT5<0TD%z1e{PM!cju(j$wX)c8o8#Y<`?fW%Auh?is*KOq4LH(VJ80QB$("
    "%mXF~xeP5x3y<V3=crwG(44h<=Sg@3>M)U&@Ce}WNW?TFU{ZZ7eLBBsG6|S8u7ih1`ow(aqPzcbaONH~6Ar4hDK>Y=2$<k-1PwLN"
    "fJtWI5kG<<Bs}7K=%f1k?n$LI?YT`n2j<E(>YoTr!tTv$8cu-a_&O1G-yR9hL?aY))LcXniebSSz(Expiirer%PHvlyrc$aA_>I|"
    "Ij&BPT}}_hL>ipIe(C!gn_fNzK?YX~&WylI>LIv*zVB>dx|=JYaLr9Kf-_CKN8vsWk-?dOgEI+-P-t)_qu|U4yo}(C7Z6S(!!;v}"
    "K*KdXID<>9hilT+mkJ8bBogF-6Wc=rI9YJvkWQi@oiY#LL^MXBkPdE99TEjioN(dbOc<e|BmzN61cIUn1Vt^#!*oR)Gw~!`qlbMA"
    "$-#mI76_^%ZTB5AE^kXtBoYKzvKP8M<^mGO;o3PDhzJtV4rmN#+9x!4gk&@n0yr!Nx;-Fty$_k_a(i+jg}7Z^9=8P8E5jw1->?un"
    "{S`SN>J&uYfy5gl^OtKhT$i8GsF0-6+;Y6m6>OR)<U}+ASaLXx#uXV?*x>pONZ5cdF0va5I)v<T0@^fE$i26sT#Y6Y8eI;h@iq;y"
    "N5(V)ifQmDN85fzorXnJe*XCBFMs>%-+%klkL$hj-xmQN^_i;Q`R+T~E5r*(;1IU~h}!`Fa^{o;3rH5MwgOOg1|*sgwGhCf(UfP)"
    "JSl}k4#k>5lPgUZd;^L>azj#w6cb_yK0dq#xOpNqFEqI)*IhG?#GFHJ681(j2V8eSx<iF@!2yvtPJyLlk%NqAk|^OwtqHUwP^Ru&"
    "4!Ir}MF+Gt<AD`SrMT5(1LB0a8<nDDpcn=0FyMZaC=Dt1%SvgK6a(biFLINSS`$yB2Hf2e38c{kB-err>k7-jtvu0+bkaNmXvSor"
    "DA8WZvh6qki@{wx8#JX3dI@(pZp|mGxEdhanvP-c01%#26vV0XsF~#U60T3ELr=yq2I@0U5<~Utg=S>qWpoinH^|W6#Gn$Sb4wPg"
    "5+C1_m;zF@29q3uq*x@HErr_4O4$Q~+^T&qzu!S;1vNR>{{Pd5#`XL71{HE~U2mVc&Q#6mG|l2l5_|FGrYer9`NV>;g>l&I8BMMb"
    "g`{O6RO^5epgf9V@U^IF78~GlidT{#j15e$rzMw&r4FUJ2o2KO>dlk5(8Poyf?Go79EEWd&T%q=lb6pOe#AThC{J)q=tYpR3}{^}"
    "TNIvFWDxZfSWVs(2a@So<^@M!H60>q?+D;XIunN8urUGBIVQ6^oyNG)(+NxHfJ6XS@9q-QJu7$$z&a!1NImT*X(0d^b-j9%cs@Q;"
    "T0pL#M$H}wShFuyPGmt;$v%N*G>pQ7QKLBP0uY}A!mV-u{89@bQzgXp)<^&_0H6b0Zwij2Yxb|s8<9v17!oi=1-KOfl6g>$s>30j"
    "pFlZErD$fN=0yn_L*_br3yqxu<{YJ$ckD8HH4dS;0(|bpiPMCDRiaO{MttNfXh3je<{N2dR^TGS=<s98#T+~xdb$Q9y#^q~#T%ms"
    "4tPKjsooh6@ZxbC075F%+z<d>B6W(sAQAxg(Yti+dJ|rtd#CSQ++=lo4yj2j=LSR}ApoG3R2~k=TuP!#W+|nwYGcn&9X-6z<B9!l"
    "Y@&{lM=S>Ks!%~ib3ep(RmWJv8vDfNS|B^KB6m;@?-3M$+@Tb{L&<BB1<#@L&@Fd&SBdtO#MUJ7EmzceL?c!AnQh->Y(<p{`~<B^"
    "9p7BDcA?bhvK0s+M9m@g@Q2vvBe8*Zm&hq1Zz<8r4k%qYlY*2qTFU?nl4sj|wk6KI!z&a(#yrSk7|Cdm5KI|)JD7JSQuhb6**znQ"
    "Pf%SZ8F|o{ZM5W)7{Ib9xuihoKu>%}`5}aeVIzAMRh`FHb4tVAKqe%b{WEI=Y_djN+3pG#YmJV&7_(Q~Eu48Z6l)|+QQTkBZS7P!"
    "ZV9lx>OX({^!ML>{m;Ms`PVzd@j?IA(_Ap#A-rMz#nVBif}}K4gCh$3ChI=zslk2%^NV8IP~jfiyHw!FgIJQ$y-`H?uftD!F(UV6"
    "=?jfcC{%1%g1RJ;7yLxA%CV=&@e*<PVX*5T4PX_bDR!Diz381r<n%HYCE>Vkr<>QQgksMX;}W*oljEA0;H8vV7Iw?(E6w|@>N2{;"
    "$_QsOw(;xH2=o@rPhswDt$lj%kCl$WyTSZ-WOinY-?!y)KHiY$cX<6b+2=R)epB9dVDA51(SsNPHS0W+=Dx|eFJ>$#bm5<5i|ZpX"
    "D-*{_kYP@>bwTCnB;(iZ$SGEWS#yd}PS3BKuu1)4OP#mXts!p+pR^D64c&Jy-~LGkv=;sz=hO_pTaF%E;kQ-#hsCJqe9Woo+_%H4"
    "L*RaKKV5%#ti>?+VO^;pXRgQomq6}+N0ifLf0s7*4&OaYlHHoy)8xb$x2H$lwBX&21#!j}Ph%1L8aJy1Tm%NaTVzCR*_>`8<&XwY"
    "jo+w(iBJm8nT3y<hGsREs203ZH`;#JY8Ep+Gt-|muIWJN>>WAl5L*^`%_%cAa^lQ+%%^(=CYduWpIPOpRsKtM(%rRRRo0IAJN;|n"
    "VSTW_b-SL(WeeSGSF;A{6o=q5i*{VE^YYXkakDPF<#W?Lop1FYxAG-U29PmkigI@%N2brsJ@RGEdxNtbg-$8ZX-#R($<12R+-hf)"
    "&#s@)?F{7FRAaQs2cdwk5bX?f@A~+6IIkCD{`zmf{P-UftFmi*QI^U=ZOdUki-YJ*b~2P{%TZ_a4Y!&Lmx~j9J*tf)a!7b1-hi_y"
    ">~*&N-yqjmK8rGN#<I_uW3*BvHo%$dMwP>{Cg6xhEw$7xLR_MV=)mGMQ=BnHI5lXb$Wjg0f-!E|_BM)zo5CB4y*HEmv?nN|zY~+8"
    "5<r_bMO~xVfjcXr<<x-IWGUb#!`3^oGpFsE-y1C4T>CDc+lsZ{SCt7iZxq_&K-EL<lr#LLGl%e#z?EBC_V`GIGu-E2^X;y}hf|$j"
    "h?=<Xv`niyw`Keif}$eti``{%jK>YV23`no6TA`2agSma^Ee7@*{)<}7SoaLP`wm^D|WgX_t?$6sw_6feNnO+l(VbN?a8$wTdEv*"
    "Wb(s+oPSR^d|%8A-i$KrOE<?n-My^$IKAO7j-t3p_U2vwov?%38mP4`km=M|o!wfMkp)?}z0Jnvwn8#{n+dvP6HXVmbpOwHE~=;B"
    "Ey5jkeCPfH3sX!{3wJ-3ZS0ZsAPY82b(^`Fm7n!e?#b>>`ifvL&(aX9a-3Bn7Wb^?)QWu`HJa{vC&oJ4$0oK?liV*fOaoA+yKvi;"
    "J9P*f8yaVN7~RS<J~^kn6~CMZCuV+U&70-)7!~vUtjkV!<*Z$=Zu2y%-b*#lz#^Jy?(=O8TG-g~aXP&}>LHDF2h_Wx<{UAHzzsk8"
    "Zs)d-GS3}e<`6p>`sc&5dopAxR;h;vCbB19KYfmxG#ER&@gOL%jv&qP&*C1=@I%caEN<d^t30o3zkdC%-+ui4M-4NWai^&}doMb_"
    "h+i!IHcLrvHJ)36RcFTdY#-Zn{F+B_)lI~#Z>ocwTYXwEck`NI(Uo`fofv@3>~yt1>C{#icavb0>dW7VbJ)|Go2~#C{&_Vy-v_uw"
    "gku_2UxyCde#m1sxtsakZQ|3G=JdRYHe$9iah5@}Ri_3+CC4&aY9FWCjEETLE*^w4=E^4?sV4!3<p)G=>u|K&|H^IqTcqc~imkxJ"
    ">?@;p-T&_0kjX~Dx|O^B+x6{0_KNh&o_oW${S>k%W)%WhL^s}vi0Bly+Z~={&Y7P_I_~>l)(i;$|4i*V`!H*3Gc8J#!aUW53?Ev>"
    "cb<GG2Ubh4a+||$_Kg4q5(8Vo1~hJO890wnx&7b=JdOrvVI4Q=4YRRF_xdvz(Zd*qn|t&ZW2;+zBjC0&w;L>gt^L~e*C+dK`Dylc"
    "&-$+wyM0THV>{|61=?!duv$5qudM|4JohV4vRke7jWT7&g!aP#PK^SHn7}+%@gOE(f6}p_2HVZF?fshVKlg(<Z)<il@0bWvt>Y+e"
    "KTf5^=DzgV%bO90^=BeZafmFx^_U&f+xRTTJZS0`=S<!5O!nGIzUlvW%a4Za5}kW|^-sKvFUizngd6v8EW3@h|KBiRdEj*sMwxoS"
    "r{k~r+1z);9o)k4zZc;AgiY7~ZY+8oHdsUgR*_Nl`0sA)MR>cW1+0Bsv4}G``zn`rDJ(lyU!oa}$?#DMXV2?<gdhL?$2&^k@dwT0"
    "qa?4x=m*!G&XdbHyngGHpaTr%bhAsm><d2(TRb@eifz{NYhEhC>=XF_y{u>%tS>I{GrhuQuh-G6th}NFX7+uP4!aDzUVb~*uUQw^"
    "`1#lOnhrm^Ma}CMY#4P3lk)r8O+*&2e{>t1-=TZ^_9Sn%=SOw9DrcCK{Z#M#(g^F8JilM2#u#B-ZZvCaMt=Qb+%U&oSleRuRalI5"
    ">kFB@IY!LdkdY5<K7!3L$MegASU$phPO)uS+dQ44!W`xmoBhtXYtR|6b>6(*uDouuUzW3<@rF4a=&)xxW-!>yhn+Y0HodSedp}=u"
    "P3t!(7oY`Yj0iiIZuvQ{f5hvTFxaQ___89k?J8x@ZrBO@avq^#eHYm(8;dIPde+wVdDA|>1LMVFx6<8Kz)Km_f?sDAHZ$hgg;hI!"
    "Ehx7!&2!;5a^aQM$ji>{)r8S#?FQ<1`q^7!lG|4Sn<`+Vpq^ySmiHjLpik|y=I9s8f<?nHwjy3x9xj$1+ER68AH2m2kCvdbW$AP~"
    "<`rJUzR5*uyo>La0Zi^_oi1~YTj*e7%XG`P);lc&n3SIxfb=`})ooqv)6}}Tby^7+P6NNQnKhgN-YVsF2-a*E>pPzOUZJd6z0_)#"
    "owv%wDL$-qv4h^o-thA*awc1pmbC}|IZ*t9TTSHwub(tCuMbp)-)+k4EnB93T00+pUVdQuDA)C|_L<mzX~Ske@6J=-?V>K9>F~4m"
    ";y24>Z3`^>+tik=dV_DaZ!sf$1qSP~pN$88XPSUT%;LR^?B0|2Y`kLkSk0?LcX_&Hi9VQ&{bt0+SfapAHWsbfSX%DRJX25Wq9=eE"
    "k^0}FTSX@fFD)#icXrfJFRPzFe)^vu|Ie@EtEJh6ZEkV@;^OK}XWnbKy6eX&*S@Wu<k<NJ%5Q$nxn;Ti#q9EBn2o%wKi=B91I}$+"
    "b@y$e-SUz`xBVIH>IoeCFv9j%S4MjS>pLTU*v9-4Nc*y8`eBgrIhUK=%dmca$2i)hU*x7;pJsh-W2>+}NOSfhMoxb;$hsoY7U9-!"
    "|ID5yTJ-zfub8G6oWA)Tll4K8fBX^8dR$P>cQ4M(FRl^uUwZa!^_`DfgWTj*mEHGy9$k(0rF+WOA^H95#wORo`Tuj5uYK41JhQ&$"
    "Hfm-0Y>NFw)8baJoqNNc-%z)GsoBHtF{Yo4?39Fic7fdfw=wSFmuD;G?(G&}e~)Io0R!)s@mnRfpAq%@tgl`q_Woy3-+K$&_g|j&"
    "#lH6Z3du+Pc7D))yXC_ptK8SVl6v6X_v;U=+{4LY<FlsaD$%XBDAvbJZmxBGrP};Tw#kjv>epM!1#mkzzAZlanQw{APuAS(t{q$V"
    "gZs*yv6y$}^#kHAIr|L0o8L$@d$s2qzC$p+Rhr$QGy7D@ZG5S;X|HiF_wH3_&V0ebnKy#Xzu=nR^1pi(+5R&kZgqj#<41nn18b(D"
    "H*bx5sLe0#>DzdkY4%o%n{M&H^x(|oQH14dGjD0K-dWo2cpJ%2SbVFa->$WL(b~=@Guj>a5AQVlgx$|FH?9+%Try<ddgkosVm3sq"
    "U!0f?uI86Zlh2>5xovi-kbXtl<ipS}P|W<V6DPe}-VHYIO^&}7^FM$7_3wZBtA2@_pWj2dxw>`pxQg43kGMskV?CHp%Gqr?DmU+P"
    "Ti<2&;PTMrm!J=wt=kWX?f6lbce<&UT&=EfdvK}SGK#Vq^PK&5+0Lz6o3p&L?k#lIOFg?cyiMXbiw{q=ZIm-do&9UxCe3*n|8c7h"
    "@z1&IZFUjbS8sc>LnrIl#r(oI|IfSdZ6na|#gO&%(ziDw3U2!wM7I^^d3Zye-}yXpFPr{>vwVKxn*U<4e(6OSX~l-|pR=38{Fh=A"
    "Z{6VbR<Po&CuiK(d0_h~7x(abKGijD8xtPAp5o?;KGnzRS0#an!u;iyStLP)yyfg)zFg#3E|pv5^uk#MZDuv>=Gl5b(zK4E?3Swy"
    "3QrpAcHG17hh@J;^zI#V?mI$6@bgz50-O2u-+KjS?=HaAy>8C9)eq)RHMs|hoaU<i1a-$TIn1OQ`#F6XRS)3Eqe50NW_sI@eixlv"
    "hkKlM`PzfmbEGj~hjx}1<5{+B-kv^xOU5#Fc3GKI%4vCh($;e>W=LWcBbz<W@|_pRJ$ZrV6U+<Vo;W~t4*T-O9nbpITc|5`ro%vW"
    ";7#Jj_T!*#d8gfDpT2t<U~q55Iu=*(eNNwLUil7|zWz_xzrTO$V!8LiB-6{i*4N9KL4@5~{+3ryuJ1^5`_Ielz4@_yTiovRVmsFt"
    "uJ4*#2dj79_1?X3Zu6QpUBxtDq92xihhlLp9S<=qyp+qwu;{4x^T$s={{4?X{_yL6w+}sxA~T|#>u18}r+D1-wUqrQ3hYROTRd%G"
    "1_0c~cM%)!M$9j=T)w>EX4PrE*!?+w=Kgt1K%eiXaZNYB{LrmVsmw#c#^W+>_ASk$r*7QF12As)mHJP3@HWho2kG4`{4t1OS{s`W"
    "Wj=X6ZYJG01GX4U-0BW?<B7YyuTv)HkY*p7e8S?REw_Hu%y`YkE#IAb=8Ui+8SWY1-kA5!XD2%$gU{*9=<k)pQsbU)-hDlji-7zr"
    "kmUA1bXkFn!@KUi?=zpiOz{Ntg~Q};zF_}6p0M;Ie!|YjD%1Q=p4;C07(>O|PO{H;UTmK{*JV5O*N;`Zhg!tLERVkK*%17N?}m&g"
    "Pqsf$Sv_v@J>R*wjsEl?(C7C1sy$@7hjzo{RhspCGj84R9(H{9@$@Yps}sZA`S&DX0^b;z*gN|+dBk3X17@fCO}EnI`In87b2Gc="
    "j}%Nl!I(ZGGco|Sd)h4@$k}|4XUlgkAE{v(fvvY2cHTmsyh3B2aZ_L2fpvZsS~nhv*McpJ4et6CX}d~c|1FrwD<N*zEoXm`G3|tg"
    "3*EgH@7Q$(PPS3czSr1zP26%gPshULxl{M-LpZm*&)~_UF`w(#-6t-gPndYVZGW(v=4S6{pUo#><aoOqBACA~ru+TuXV)Hmr19hv"
    "3d8#}4<@MN-Oh_OtHFFeo@_)Utgrf3&N{d8%=9N%CANraPrp%k^dye?z_aZ~UQw*wwTh9mJB!@p%A)I)`@jF~55N86KS&hekw)8v"
    "JpB~W_?E%#e9ExC2xZ+W7Y>o-nf29o4{j9_aC`AS>)xcj_qS%}{TG)Dso$14tCoyY;_FAjK4Ia{e|Ybbn+J#<tdE`knbhKy`uQq<"
    "Bg){O2N|wS##YE-5#XPEudoh5?G()7o0aLzwFp2gAN|}947iORG5aiH<xQPjm}PmB-R^x?3xC2hkGJU<nLFa2#%{kavY@}}zIkiM"
    "7tM0(8aDxNJKZM{`sW7hwA}qGH|&F+)9VIzVt>M+HX9Ho0^FQ`)d}6h7{J`msJ>V4CeOx;_u7pwKfv%OSvHt5wddR)emVj>5gDhR"
    ";}jn?n6I?kUu8JuiwjV0rIJow*!V0$-fgvPFYv$(@AhsKTD$`9CIB}R3iGGs&3mu*2J>kcL5pkojWgt1&%tkJebPtm3D{Y|FPKz;"
    "dv>Rhn@If%i@F@$zBXy)I#vA;#uw7=={a?6Q490e-ya%o9x`8UTJ+=aZsEmVx@~sEeD1zhzq56tw6|;9)(Ic*IG3x-nRHs)%LU)^"
    "8N%vp{nYO@?FOH)rha<I(p3I@KevB5!=n(w)+Yj!4^-@sg8kXQb+gdKM>YFIX!6O>`ht)L4(%<+`-T^L<{5qOV}{k|OWWS+1@nX6"
    "^VZw!u$zZ1-x1cs9d}^pRrG*NIt#h=9oMsPgPZ#C_dg|Y8+EV|v|Aj<f1kj-*U2q!NU|aa&bVd<Js1Du-~aOCx{v5~+xb2-zEXkA"
    "lfFuYp1Su8l(I>2DAgz(qHI!V3OBEST#DQ>Zl`XU)DWs=S{`JMZ0&11K}iK>nVXauD3;OOI+j1Z#z2wjCUpc8KACsUw^J)x>CWo`"
    "OiHbE=Xs~~py$sm+S%OdRbTPF4N6-A!OdHUGyB66+|UlwdYGrQUQGMny&`^YHLVrBg*dZ3S7qiNwJfV7-q8@I`LkPOSk$Il*g0!w"
    "TKl9ed1bX#64Gipg3U^Bzm(>E%x$zRXN=HN%D!dm(uK{^)$QEjbB}6zmA^Hg`$CObwKAvtga=~6f^xT*++=xir~FidR%kHEu3o%u"
    "*_45GIa}sPDFq7KZA70BYc09Q)_|E`_n@5Yg%B7+)2b`EZGFzb&2j{rCBcW@S(hKS0KxGTEEj>+lF1&LV6u3eFOIEcrdPKfdb!NX"
    "T3;67QgV}qJ)3}Mxz(pY&1yF-Pra0!G3Dwxa!M;$Eil}&j@DMsWbTyU{sv~ZtmmccmL>1D7Tohz_hj?7(?Xv2Mz>k=`z_L$o9KC;"
    "-qE+(j;==URo{f^*2-;fT;0U7-Ex`tO{Xk?XDxZQZFUda5*RJgi8YdYqX)Q&hFKqT$XT-<iRP5+cBXBZv^Mw-ZswNTwbPdJ^T$vB"
    "_dovq$FINr_@(&-!C<@Luap-Gyx7fvQJh1H#b;^Xq4Zy(^lxhiBE@P-UX;t8W&V=s&C=Cu@r&~Gll=KbDY>akzflsJOew`r>cLOS"
    "#ZOAfD|z=Mw_eRHmg!h+Hd|oQUU-hYYMIrRbjyI?p742=a%$arGN5RDR-1t7SfIB-uTna*|IPZ5pY&U<-KqUg&)=*bw9(B^da*}s"
    "X<lP`d)X;ZKKAU6nDh1`t)8{{b^ZCtY%#ZNuFsqG&Qo?N!NlsZwDF7aTFa4BM<Os=s~48}MIM|=sg<WQTF*{yt<rUiS*E4@bS!X_"
    "^@KClA=nLPm5ZKRZi`#A5I<S0>22N{GWW+U$>$X(rxz|ytxf2ZT*|D~1rxVw^WIz`(fXT>-ZbxfeXQ~6W27@$oo1OwdC*3URUTkD"
    "_VAQn_DyZ&7`9hkVRH_LMW5c0=_l>QZ;s`woras1r?uLa`<2<c)o-omcWhbb*0Z%DkLT|0Wk6Y_`^8>uwSu3oF02*jT*`VE>6hzk"
    "|EPuR?nU7nTgZOBTX~pSX6*+3Vn6nz4cep4Y#(R!My(ZiL%XaoukMKGUTwdWU}B5D;#}p{(*ArrbBbktV;y4ex%|fZ<>@%zW_yoX"
    "h~FIfp8GE5ElcLz9<O)D<oQm+8ST@n{dR_X?rGC-ezMno<^AW6pZ@EYAHV&3^9OR*Bru0#5H4c-GzDxp(jBtPiStBGXm<u~ZYSo`"
    "D4oIw;xtoOl*G^ww!%|0eQQ^?mOoH&*2zXNY8ur1xru98Kcxqg`kRN}z^pM~R?qe6<+%#A@N(JHFbga>cDe}6bDZ<@Qt;p$U@&vU"
    "%Pc(R(+<Pz;AD>j<M4zm3D^qh&CiX_#-$w%&YbVu##v%nf4UUd&Y#r-+;$7m56!^z_)?gjbJYA$+OeFlaf}2Ee~UwQ!t$gqOhzd^"
    "*yxrgwRs-wQ;+lGV5_j?-kC&w-kcq|0#bsS&&VypyngG1DL=#pN^ttUGl_t%BYASt5H`+Zy2;@zw<!5AJ>2J(^{{s^ZG9*ZzI5zx"
    "@A%-15|ke2HtT(U#7jSQ2+LzKdq?}i;uym0I~2DF+Ru+Qy5)fkw^>TT98tg+=VvQb>#&<XCd<AF%Oi8EBQ)^nxY;a!v|OGa=96pa"
    "nFdcTO?q+^W_DCdtIbup!190@OjcyGysy_9>%%s%Jk%xkE3?)!FY7Q}QG>A(hs|S#Zt|7gN<-K<g6NjLV`t|*Ysu?9o^8u)#}13H"
    "5A`*zd$6P3&AVG1{tVN@XQ1w&-J&hMQ@4C4yw{Ir-^aPhH<Ker^lK!y@Rh){Hr+<gnbovg_KwwI+Eq(-OP`M2$F!A45bHYlr{LWG"
    "SKON=O>!e?f_LF_xCj)xU0`13418dA=VYZ6li5ucr>0wE?mpp$O;;HFC$mNv4AMS)x<IiQ76W|a3$3m8I?<2ce)#<#|M=<W|M~lW"
    "{`B|z-0=P*MEi5a{pr=`Gq=yDh~Z&PQ0t4F^4`{aZ1=e4V)qo*DujFVQ>*7rt;^4!Cp&eO1(fJMpMrCb=bOW3v=|Of5ucqmhKEz<"
    "vNwREvz}HDYJV<#e(uda-5EYUTdJkW^{unCuiE3$-5;}YhbMkvdzRITSrDg>o$;2_$J_9DLUmtapXBJNCZEM@cf$DmT(o_Pe}B^3"
    "eRRhD<g7JaG5DlTJl_a$E_bqe=pObQ;OO`t93B7Lua3Io1C)F&{OsA2PPwvg9k~r+#axqfj|U;)OKW>4tA{7YhT-T?FKpL_!bb;w"
    "t<}-+g;hCyokKe$dAh1|c4YeOIQ8d8nBBKekIFtDHa=S~+^qt-$Ae#PbNKMn70~_Rwa*U6o~*~X$Mr&Yv|jkxQOo^NHruoFW8R;v"
    "ES{t}b-eV)EV!dcgpZE&>N5uT!lBwvj>@{nk&Zjq**;(8+#j@t<3qe(S-0J<z`zG9*zRae>GLlWK0gY4y7v4$x3}gN?m*5Rt+hQx"
    "{```Mv$d1YO9i$onegrGJE+fB0Z+e6^6Dxeh;<Y`lH;>8XXgE^{XOk$pL{zeYdLJ!p1*QT*lq5}bH`sP{n4~fj~<_`oW8#i{OKP*"
    "{rc-q_wV+UZ?F74E%mb)-yiPhD4s)mE-anP8|m^nw96>(=NB;GNx?1Pg}``DgisqHuxFai1X3q>CSX0^7RQIOuWMQKn!;;ZY~}L?"
    "(g3gq{G8AyuFC>WX9{K%+Ami)=5<&3O5X$K^S3ZaDwsJqrN3vy7cMQp_YIb}_yPL%@eRcrg5map+z7_Y*GDK?P_P6+3R)0ILEx+?"
    "S&>=vro})bv4QFqT23Sj@@j_e3Wee|)jOUY;MM@=t^tYa0PKyb)JYwJ5e{|C+&D{zQ<e5F>uKiPs#3i)K{|r8VkOSB`-0V2d*oqp"
    "Lhs;-kOELGI^t$0Fc~0ZfK!G{z&eJruvZdnJ8s$m1k|^T0sscOVc)OR#gx~09WbOe%T3C6&eG$jl>3H$`6mmcU_D`SKp^7^-y2C2"
    "`Ob+Z62AdPvOrR^-ZWzbc1XlNr-=YY0+t#`pa{{Er_>7&l<pu-sJx-Od|tk1<c6+RdL60^`p&+V;9y;y71oW)ZzwyWYd~S?0;gc_"
    "T9JVmK$!a)6vuCk49rU!g@OSE>Mh6Kym#5=NHRY$!AlA+b>8s!UC238;=r&oH&!SwGoDv?Q?@Fy1vwK2s1Oyqjpc`lLZL_23cwqq"
    ")etI$5DSp9Hw)atJjX_^5C{qp9u>j{8%C}@aT>n55gZnR4Yk6`RwK~Z49qJS;ON&!@GKCZVp5@_82Txuojz801!K4#J%fSNC5rK~"
    "XLWAWX;uvz%i&V$H6J*3u{yJOv_Igo4RcsDwN{CJixgTc$NL}}O$EApJ|g!<5+!*Hatw)-1RIF-+JROW1#$~=3-RC5HDB1*9_TNx"
    "@8jb-8TFplr;EPdUOP_iFVsfr7_|598@qcmnD5>1|4p@*(_m33cW4O0eECoPYs_FmWE_E65ktVBwxlrzQK@i%3sGpX#;B!_s|EsV"
    "#O5i2hB06c56cj9cqH0J$poMSQBNpnWW5HwFE--!W7LdfUSgQcrNX$#mkANTlZgRkv<V2NbR?)8JkFnDmZE#O)R8%f>Z*YtnBz66"
    "8wpGgMwS$spGKj1W*&1uNHI?6i*5}VLt<_m=){&zp97z^2F~z&4mu~tjx&geN4|!)h^NjsfQYmLNE9GC0u@P8Byz_h&21upUjSN`"
    "NL)waIuh3*fJ_}50AY~zg+C13N(;4;zXO8t2>={$3kW&@&1~cV5mAA6rC|)u8O$tQfkYBl3r}Rva|yF)%-m*P%czTiS3xsdSLM%1"
    "eFiPPj%PqC!;!5VN5+ptU%}6JdQhHMzx;lli|6;VSD)8XH-CopT;KNTv$i--pTSPgGQAuu?x$~KIVKOl*gZhI4Ic?C3*DtD@Tf6c"
    "8UxAmN&3bE*zTCLLJFH5mf^trH=ll<-)@8Q4S1`H{7F0a&Y4R~Bu}G7I&y1Bdy2xsDbw~$GQqT<+vAaNA9@BGIm=$$SlIibm!Fm+"
    "I8M_`8dN{OQeUF@ru{iCZd;npOw;3H)dIUl%DZax2)f5w=h2>ORAcsn2S?pD6JH6_Q^7x_`AwGo91HL-%&q(X-51)B_(uCzs@5OR"
    "gZog+z5#yfnKL^=egT!+beS~rPWfoxs~3prv6fve9C)oo0v>c~e(p*I4kM_^fpT2Y^3!fBpbQ00o_3duozyeGxk5!}x=oZEi?uw)"
    ">D37Gc)E>+GcDR7J->YgX?dX6h4RR|O+0m-){EL7XaO<Ua1SjG_lo|YmY?JZ4sxq~PU+1<a=YHfvs!L3!E6D}d|SYA<j)3++UUX^"
    "43zDfY_~@LLG6L<c*6428~NK0l-;&}u_g(h+4I|B`ri7pJ$tJ0f+K^P2`8$ER}10=YAb_HEi}|Tjp9Em-lr!uH2&k7AO`NE3wZX%"
    "DUA?F_qVV3r^74z$*aSb7pTSU52mZn<70o&dSwsm@ifWmR9_&1sP*DcV{pA8oaf1J$LC(FLGH1Zz(IHAw%wIG?nvE-0|a=~={D0J"
    "?X~E4b7H@l8|fvno7K4OOwfsC3~#1|KOqgil;#fRR6H&}e*57szyAK)Z-4#yx3)I;8ovhUHkUV`pP65eFZzM|OaB2vlnCTwc#%kc"
    "%^s*;h5Q0V)mAZc;xM(_`AC=M6znw_x!+_6z8vEw>Aq4{PKk;WIdxwunsYr)gn-lrP^f!%=ChW`6G4UAUQ2FnxgP{%<%>P)73wKp"
    "!1AR;*%?$jbg-)+J5OQTc43n%cr1cl&E5u;m7N}OIBOHq0ni;dYFfBF_FC;w!K0RQrc(<FHnj*2isqU56|e6Pa8T!vY4P`uq$V2z"
    "$yfW74X0nU61;q%1kVKgMN8B(gQ0!cwc0}m76I_LU~iy(dgj<OB82|6T6YmWxAgg8+#sa>S==Cu&+CRuc|N<TuyTu)WvYIgeS6Eq"
    "#iD|rD|^oEv&CuBC-PP0KrUPo9_e^L!*r^pJDQ98IU|ktCz%oT1r<jg`X`Z|RSu8haDSJGYfHkNE%fR|0N*}qqZM!h&_54+;qtw|"
    "1zgDFB+OaJD1#<uka~`;22A5u+g_gD)xO;fCV(`+d{zjm#Ci^#fJ5X60|eqmTv0O`04s|Z?hAV3XB5JSsBw-OfZF2y9N4q0QtSDm"
    "eD7F|^1uPlT=LvUAL$#uwG_u17s<FUBsil%l5hpbD(2m$Nzm_ZfK<$ZETP1U|L$BCGC8=;Fa&xZHa?j|#;Y)1Sx-sT0Intja3VBl"
    "gy2`T87=EBwHL5rmsJa^xd>x?1&au*r%;A%FR-6q@IcVUcAV_6vhA2rY9@}qK+VVt_UZZ<^e`7da{)Xg#z^=f8&1uYh}b3*U$DCk"
    "hfywiV3~_AIP!6<Bp8O^T$9_I!9Kx0w<JGc1!_CWes&mm)?pK4IGJ1>)$~uY^I;T8ezqPfaRO^m;30^HBB!mJ9A(u#F2J~5zMW;%"
    "9W3m8oqJv>fz=k+b#<TyRBMoOG0p9ldQR5IUUVL2v<5?$o<Ylv^C!)w|7?kFTj($Ndg{rNqx)FW$+g!Xzy0u^fB)sb|Mt&c+dUoc"
    "Z^!%93hyI4@3Sqb9Zwl4si(Xz!0;p`n<-~9;V>nACi6Z<^dRGVN)&c{k3mZbW(wC<&$Lb7_S%SVM5dhicFW*0l`>#@4cv~cjl}xI"
    "PWXbIxU+MR;{R|;WWJRH-?WsZrW7-U$QTjbrhMR=9Z}tbL$CkE+VUTXwTRnSN`cBmWG9<4`5`~)Sf*^X71g(u5=Pl?Q$~MMNlFqa"
    "9;FOzOQxU{DTD1?Go@@(lA6LjXesch4W(qKYFjBF^TSf4HjuGqDOei_JD#LCWCuh_RZ}!=Ue#9B6faV^*KIB3Qlb+`O5`bOeuA(w"
    "ypE>V$@DszUMCSZFH*Q~nWQ8&rK%}f4JjgJ<fo`LM5bWhs;X_JXkK5Y*OwK8;;i~sKxpg#U%)E40#<&Cx7u9sR(?uQJ)kK(Khexj"
    "6m~{_;;h%Kd`hxvd`YGqv+lGMVdtGv%#>=Tv<3Kzd>i?>hzu&9>a3jhlqzFgL8QQAiZ``+QzjgwT(snBE4iZNG##ek7-TbL$y};T"
    "W+|7N;z&w4k{Kz*)K(5X$fmX|v?WER&XlV9mXz|5DI;$6Atfr>WD1<8%(0lR4acCWG1z;3nRYJIHz@<EOg6P;A(M964BvRk6%jWz"
    "1|sDWDef_+)%3cm+KQR7WU`!>tQs#;qztXSS@B@DtXqprDLn<-nSF@xAd?iFAF9o^qo>$*;K+j$I~i%~vWgu$I*ydjvmNx`9#Jjj"
    "!~=ii^<G;VZzke(CMllfhsq>XhNncHGFm@M@oLJY<n$@U_TV~BN%OsZt>}zirq1!(h|cs{q)a=Wcr8+<Oft3MlsO(1F`y}^r>$V7"
    "=-QHyK|O7q^HY)X6`3!jluM*kk`hdrfMQV1lp!<M4@m8eW86zphPI;0q&dFUWY+o)Fb`G=_ASm?K~!R(r|2@nPB86wkuvP~xmv{S"
    "fSQu#tSu_Bc0?wk@$Y46>odyyD1%e#OaW6H(ERk-ZbId=Pf2sWofK`E*umP8>U9z+SX(q>V5bB#qQQ)tH?_%nFz3TU+nkM>DgFbQ"
    "`k3NANGYR6lGd0+3NGz3+L2X5`bwjwt%|m=Pe~#L)q_;5oGK|rO+h7xR)Wv9WmQ{LwGBJTj9V71acE1TChk+x++WB_+-z;}P@68p"
    "T0KjV+KQ>IC=m@JrJ6aVGFpCu>YJ3oc7hpEuX>P#*U`)m_RY@}9#K06pZHdZ9ouUy#eX@aY(0QS-}X7phb0G(+AflkOl`@`4}Sw@"
    "Ge4iETqGsQIR^7B3vE0li4;8sdVZ4WTa@#K6wDN_j?$<M9N8&fwDW=2V|IvSY~O(SCQ_z0k<&5DVJWtZ?b|km`4&u>z-I3<MScas"
    "W$K|F|LB4H)4ayM!56f_2im?WvrlmcGVZYyY#A?PbZy=&ZJaXpgS}}dyuX|JZ$JI~x1WCfU+?dxV18jf4+KaAOwKrZpaJx>0#!ng"
    "aaIH1+qzhMAyWwOshM$70^ElbN6+HmqdGIa()5bb8z0DXrAJ5#qT^>L9?OP3ZkW!Ljvh059PEUiv!tVgC`n;Q^qeFe9R-Q^BhW`j"
    "es3eNXGRb75S#HhE}6c6lMP)u9hNdC?dbtC{5US7ww^nk9Ss1+ww@V%|2WRdo(j9iQ@8L9=z#{OJ#xFIAM^yNcEFc;33j}QW1c>4"
    "qREN|3qP}YIV+XMKUF!B9Q7KvYWJ>fB;+@1NlH7*q7lQc&1bzs>5mneuISl~N76Z6T30#yWT$qoq<R2GL_a<O`I6zM1OZ3*KA8rQ"
    "ojrua0UVlkxD~~&{aQrf01i<5-HHoQE)DSbyxCnZfdizExoaElqXclDyu&@{eXPwR@9%SMzTgJ%cGg#R&XfSRvllzM8c^}H^S7j-"
    "+_gKf1GNGBb{|*^_{{BnFcA9|?xTSCbXo^E1=ZH@E{>2fC38bb1#sJp-2I^E(6f_sL7Ym)^|~RBpKRubetkvFg&}v5U9AwEC`5WB"
    "&!ez3AhQ#W8UV}mU3*ZR8W1^<xDrwY3zsRQ+D<!#SLBL;l|etAXIwlFokx0GbUhFE7673HxaC0F>MU0e`~bS=wSy}5OHEg73ppyI"
    "8KQc_qZWn1)rN2Dh>Rr_cL1>J(ExG~zf-WG1(9OPvjt43@S?0*Q&NClhiYqn=qT$o5!wI=G&(@h)L8%n5SP8$smx!lL*3?!^+ZbN"
    "#ZCtg<OR4ZT_<HbfTXHQ$%<lTo7M`^(R&dJ)a&84E8{NSLWQ3)o*fpf-iRIRCVfqq)tDf-+Yn8vy?V(3XE$Ega}aa2m;Q^r<53RU"
    "C;;c6jTACF0}V;sj*#>rN-yBp#x?v*evp%Ac83CZRMp0i>a`hUxpjR6238m@dYwdFcV4`J&wJ;@b?H+EnwcH<HfE}1CfaP_A@Ced"
    "BVX7MIpP~Z*zkLf-CuApyPWes+yJ%dB&tyCiUfW=!AyR^nzZP2GWB|)`O{0CA>q4UUSQ1g)I-`Y{XDD1JvhefgwKzMwqFmIHSIm*"
    "hx897&!4ej&-UAiCKwe&))%kUJ~h><xi57U1;!-RX-hH>jb=_#NfS)lIjS*boeM`Vb;>Hc2GVor9ZNx1?G)AzDO1?}<HeWu=uIpa"
    "s@Rv+hgzNNwOxHQ`)N5lc8`oL;Lm{VBJO@pPJsDlHI|R@5VsjRQ1b^Uy<7T2Y7_vgwU;jr7Bmdt$8SIU$3K7n`Jcc4_SgGFb8|Jd"
    "6Y%5b(fZG^e@FZQ5=;a%PE>5cjx#;<Ldx&-fSxbd``i(~ti$+~<)dhLp=bQM-iZ`!@^x+<PCbk`rxW2)pdkLUXaI|b|HMP8Cn_9Z"
    "d4E7~-oda1!WJMYFKRd#k%xnt078#ef8ea#NxlG;phSpfqmBXQyg<(?>_T>yd0?5BMflj9K(9dX^}-<44nAvgXPTco4zpQm9S80H"
    ";(=z;{TWeZd52A>DSbY9J$&*~IeE>%fpv}qq$lDRj}xyV!husgcc&Q-^lUj1BT;ZPWYvu%IB9VrMK~uR4+pa2WP_8DEyRiEdUDqz"
    "5!i5wDYZJp#wiDS3PP$tYz{C^MTq27gM*O^Be3IK!k-J}eduwvRKKL}LbhzqEK@0kIZ_HE-f^k6%%*W}1Qw_DS{(twL46&TVw@%A"
    "g_ILW<9LC9f`E`(IVH$e>KN%|5eyGa1awXin*9fwVZ#XroRc`8lpvUKUU>(BkT`Qr+#?R@ku_X$jGC#ol=&9MNE9taw#ulsL9et*"
    "r6-a7Mm2hpy6tUFq^zE{9`(j+5<+@fqvuC`cvKOuy;Dx!G9SO2Zd=)WdjjKV@8zW@?K!YGQF$+OJ#xGu#|aUQ!|f5sPIFo#qPUmZ"
    "kD3A=5ozN(uZ{G+fPARO@CSq*xis)Frd1JbY`k4e3EL6%!vr2q=OF%rWe7N3@;Hvz!^{qjmNWe0(#gr35l&}+VAzsN6>yZV-6E0S"
    "+0qsi<TAur-8hMu-&x<yMq!_?ZCM=K`V$rh;dEsn{fSGHpV#N8EZu&!eW}*NaXmb4-O=h3{K2BI-}kgA7azPGP%eV-C!p4}?Z@<9"
    "{RG)8tOv0q9k!)&;-MFLf2=>7_vy)c)Mk@IEsJo_3T%I#HHU4hd@PGw&yU}J`1ybR^Ot)Ur+rUz$L=)-&Iefgfr9qwQaX@zpPR5T"
    "XQ@k1R-McQ)mE*%+D1(aUUkGYs{3|k!5vy~2f3QF!IwXD&F{mDd7t@)%d~z_fW2aJY;Uw!1{6tbz%S7Unq^d@=|)k>ln*kBpsi%Z"
    "G)0;1?VLs%ZWQSTF?oOMI%w7GYIqhtHd<IdpY>Z1H+g?cta?^HD3vPxucR3i9<_a@l=|(AdfUEC(CTur`-P4E!)hxq?1wJvj3#B|"
    "fYQ=Ko7FPa2bw+H)#}u@5EZ0x^u&LHDU!Au7uV)D+C28-Vyx-LoWCztz`77b-@ZYrk5Vv7_akwCV8E3n9E`Ty80L0Rx)}7Gma3#7"
    "Xw<zWI+xJiwDxmLMKM}XMk&<Fvy0-sbwa?PwMh4#YeWnIf(m8@41t6i%defC8w!I}u^?x~G3~uD3p&d$mXo^JDzOe-Li<IRo4@~6"
    "F#-a)Ic10R!p(G9pCgFl5hu~@3XZ@+JmSP1(rrayt04g)cNry*npgWttmMC;&a(YpSRxI-W4IYk2vF^8SR@r2VWWCp80w-8OG}++"
    "n0ugQMP0_3Xg_<FGS0-Hp-fB~GJ!>-YSs}^C)5?ygxi~-uDGX6I3;vihz%?~7e!QTL`60b8<k_cLa~a6?G{{TJ5OMg7b&lO=>Cj3"
    "Mb?pqakuAq;f}UJc(imM_m~ioe8!sW>TAD4cQcNeIFdSsMH??kPm)55Hr7PjkNwdiBUsCR<g_X3r8ZiK4FlX6c?@-0!<?kKCt7<g"
    ";!!Jwj2G&or1mP-F)Ui7wnF?M!vqb(!<r(YtjzAS91tZbi6Jr2`TnOW7#?0F1&b<1M`m)7MH%@;Z4{|Ma&{j~NjWrTSx|<qURf*f"
    "V#>H1d=m^5hrKaZU~>^Krh{zlsF)T=)3WCoPUZ{fd@9SyO`@W1AXC3v9PBNT>*~{1J%>;}+x4%6MxkD#gUo07WKGX$iv=V?e1*xe"
    "nXjCf?v{?q*BxP^&YqOB6<Biu>(xpr<7UlZY39}SQP7%#5??qqtF^X)IXRg=U%aKIg`Hd9A%EA|KVg|0Ki>x*eUcV1<mi(7oS+iH"
    "{+R}WGTl{wLy>M~7*MdF)fexe<?0R!1~j~nGDDGWM+oS1^@J54ymyvgN+h`YC_Zx7I$=Rif@<AN+Qx!>AM4oZ{>vH9|4~=W{Smap"
    "WNr`H`uY&ZpKUGqjVo--@Hx?ceNW5(3%1C9{Px4IKmGR8&;R~!KmGk5KmFT#ORt^SdKYCoWjcO+bKRR1$ZwW<^{E{}3rG&oZ+L>R"
    "uyo>I`vjr$`%Jpatu&oUt-D*!J>+OTt$U$7vImGMEqIcLF!P7K-dpF92lf<<+;V$7jg}Gj+MzO%C5F@7CXLE*uch3|pL?)Q<EfRH"
    "6$wxxVQI1R;7toui|<Uw>^U`NG|j55nxEdNpS0!3vc+lNXNq3QhE){d&{a^<v~YXUBs@#gG9?QJ9*Xy=0@+^Ef;q8Z<<@=dHLgyy"
    "$x91%b%Jem(kqEqD%Y;uy{VIT6<>=kj-Y3C5FYD<n{_E{?P;EQqQxI{KWEX^x)Eo*cEUrmmVWXaIgtlTi`!b@uN}LVTRHN^OWn=a"
    ">L>Zz*B-mGwM#|!({IaG8+`EgXV(cJb;6li{DBrwU-<e<$SFB;M>?%|`mIj4Efp~13F=_ZwxE}^Q~L=$4gbXaUZ?$b+T}qTAU>C^"
    "GhXqqk#lHpW%ZFDEWp-+#<XjQ>(O<Oa_(Vx`sAlmo}5y);lMhr6K)#`t_2P)Jmu)E#T$9h<LL~Y{=v^(<d;rMi&Z~$rdOtpGA_ZG"
    "NP?ONujE!vyH2M;&!wW}-6__2`FUbpGG!XDG%L4`l_r=|aeLAZikzHUc`;3YZbyOS$gXEvulRW$G@V{d)AwnzG%c^)LC>!DD4;O?"
    "<5CLug}0Sp_DgoZyYHo(=*yqwc#Au?_r%l}U3Twj&FgT`m&3MxI`)>aeQ^&<T5^fv&qzCs;Pc|%kKcayKmYBg|NQm;`03yO{ipj&"
    "|FyWGjiNmn)p|10@{9>&hKom%bms5LT*EUaFzaE?8T{5WJiE}CT+S(4K$UZ5BtY>Kl-zPAk0%_->2cYW11Ry-BLSP3o%sUFENJg1"
    "FNdH;;v{CE)GV(&d1EcgE2D;eJ!?-v)R3V1qL=Mgo?vUiegcsO+t&CTCCvhuk=N7qI!{)0^jZf-?SV(@{@}@zc>3)srzdaD(|BtA"
    "i{6JwEnwzozf6v;gJS);G-YoJ%6iOM4YA~4D+lJP+%9Hd)&j4r>YQr{susOe^s)u>$#2uVxdpQG#cx{NNb_oI)XM#N-C-YHZ5ziw"
    "#$^|!;hAS^f+yDZPdpNSyXt?s+2sw-U|U;Hy|z|Tc6HEi=FooAj^JQx)*BXJoA<D3NB#?K^E`h~<#+xRJ}y81f%V<4o8Pol|ESYW"
    "vv&v2+Yx-!N4ldu#+??ts`FHPc99684*Jc=SR3zxIV<p+{P`naXgT<YH>H$=2Vb1Re2Nlm##v{v{_2R@3$NW~ZejPk-mJTyyl-VB"
    "!a*c<vq*2`U7wZ1(dhR)g8R5Udkv4XPb;2h^Uag_t>!hK(e6EShcVMuGT>;<Lu;GxIMe4VAZ}AboU-}@k83RFHB$4%Z{B0n7ti*V"
    "cTuvL&#N5z?yfgxk?t_J&uKe*Ppee>yw5ek|Ni@5e)@a+NRaNsyq{wqn>ph{IlRB&*&3=B`vyaf>h$W~2VebMOsYkG!ne04bL5pz"
    "{|3{O8HhLbwF29}@oe8m+vRd%1$TKS%R!EVslDC0`r7-@^WN-5buR*D+Osb_E@0LWV37x<q+zpjrbk|zS7;@6>NO~3q|5Pd-{?;3"
    "-nui=toe^Wn9;%JBgp*+l23AfBuD#QZQV2fQ69A2@L=xL**axk5R83Lr|jZ6wXL`Z3x3;!>HCCQj@%bk06vMeH{$YCd+b>-n6cKs"
    "Ez;$lXP3_SggtD0@$7p~y~K1a?&t$-%feG!f|?`$nD<>dSl{ot54^U&opNk$w9os~7f~`2{-GRpt0vFBIPuk*H(Iefijpkbot!hi"
    "(K~A^?s)Z4uh-6~b=H@RC!RSYW_Vop{Pm#p(>>PKT}$=Ht^YIYQl~raO`TFh!luOhQJVf0p!Myy{=Li2!qc}tXYY>vmyB-nMt55+"
    "R^+X3eZ2Ag<>?n#`>~W)XG>4t)7d(mc%$22e8JqaaAKa*_A|UP1G8r+&WPu^XP$Uw&oDiyk$N7S`5m4!Msm+gFz2_{$ln_?B7a~("
    "pGj$7BwBKyMo^ZfCo?I3tdsg;mDv6(IsW9gOj_={I_O26(8^t3yEsd;ty}iAxac)YTJY*TNBb_$llr;KyY;khD?#lUWSU&>u@0Kr"
    "<)^Q)U@d+t2ZmgDs6Ako12F5SD_H;fw7oBTKkwDR-~R2VU;fg5&hh=LrSBWy-uK<zgMn9V2pk~JKwu%)BT$ckynyhn=)iro&~=OC"
    "8we&4Fwk@)&Ugmm5m4F%Z*Ra$AZ&oQW6*&#7zAjHcj?u3iQT(A9R}(Iu68-zcgEG0ja|D@ZvoJ*;lqptzz(Q?CUE^}&-LiJ9zPfS"
    "Tt0u!y=2tqET7ZvIlXTL;LojY(C6B(V7v`5AQ7N&h7LpuBm&ekM&gXLV^o!qAAoYeC<wSXaElZ!Qn^Ug7#FHF==rV{7fZkF^j3=;"
    "0Wt?D<1S|a0+a#NCDQ6<p$r1}4}tGN2&?N6KvEb*0a|5AU8Doo1S$u<GZJScozd>WLyTxKz61FNf(nEk!!Jf5Kqi1k0B{C$Mlu1n"
    "bW{Q)0ssPDFlFw$?@IfD_BW>^RYPL?;d%<(dIyj+;CAJ{i%$b``{DQpAY!0A0=50j`vNWl$PKs}kUs<NrY@1YS%qpM(0<yzhY{R@"
    "3WF}mVvujY$iBs3{mA+m)+$Efyn?X6cyGJ0V@1I*FSVZ+AJ{u2xkKMY^Pn;8O?#I!#0k9zHC3`0G+9kBb?EA>`XO{*M`W<R_W_Zy"
    "I#eVySzd*{$3Vq`H1Gszk{$C>)b}u6jP`_aQD`*4rP62}DjTRSsH}K%=zDRx4rK|IRnIufhTc`Lj2fC2Z42EO0^X9bW3geEgl<|;"
    "Fn@@FVitPX2KH{PqnNR*le~Oc7*MRv?qXp@;hC6w#xlcP$1Vyb6GE9ytxrWrJU~M0uH$m5BO$=TykJ3l6(CK%Az{@kctEbN0It2r"
    "!e|{pp211Lx3{IAK%fBJgP#WY4G=JpIFKh0I3p|uC;+sM?>kT^;3ZHspxy1AnvPF^YyekZJ`vCTeF%;L?Gi}NXh?02_KWl<0s<kN"
    "iz2WPZzJ~w%P@Zk3L}eimwCV(5K@B^C*mo`cSLds5}pvZkTj9lkP<EA`=2;!2!c|F0)wDI@1OeYNH^Dz+_M%xLW+rm4X5e|U?~G}"
    "tq>d1yCIGU&edv=SApaVz!9Kwpsh4u!eyqzy*5_Kb79Z<Zs+Sc-95v3I)84z(XgJw-F@No)}8rp_l5LddIa$Z+GF_h9zA{x+s8q6"
    "tvuAnXgnq>HC`n3eza5Tr;m9(u65l+A7AsijF%X+wy8hgub;cco6kW$$N7AZro?lY&w!r&O!xEo9u<k_w%*d^Gkc!teoVfjoAU1="
    "9e#ebS=u!PUTr9SEk+w|w@Lq4Y?#1UpMd`2>Xf*UypaBS?3}cayb#}BvPB@BlN%D(4nn>c%tKp3AIpMoBrJ}JwEc_My}$8)|NXDO"
    "{PNR#cjI1-f%_I~H>R!~y03<Aoi9P|@$~&>$O0K0-;n!e^A3eJ&FrKX2ndmEx#`kS-rijulr*X<5=UQi0v{iI_ec&$O3SlQo-NXF"
    "y|aYD1ua^Uv?60#gh>;@*^#8Gy1;{czj7n<-~|nv+9yjQ%yU92Z45%3x{(n+gH?!fl$)rs9F1_4S&k3dX_oIcabY=_zR!4qh)Wl1"
    "nnn)qF^4-=ABp-RNGyj0>(v2hU6VYdE+Ye1<6!j;aX^=1$g-A2-2bJd!(x{4{1ZruIVIp;DHl?;d-<{I{?LC23sr+;-ynOjDza3y"
    "X2^Sdg>-RE-ih8~L8B}3K=T}B%VD&w<RQ&Vn*S0lN!kqsoX<{jkDNdPhM`_dZYXLj>_KiU;wZxq&2d)3eo3S>glNC9Otg2%Nfy#|"
    "&y-m2c4MSk-t(;s2jc$4C4UjY`{$qnu3-0%Tm@SG_s@J0*8Q7iZLNqP9{V2NO*;fZ3X((v-!L4&a8FlAWEw=8b+||DI1CNB1VTHF"
    "!NRKU^)8a-8v)`%BH9;JaNI*Cz7JI)iu`#y!gn#?GVM?y1wRYR(+p~oRYKP}R5b|2kFnf`B!>nDe^~Iy2MkqRuGokc_%G!dIe-Uy"
    "j}B}!7n!%B8zV?o5TR&}`e7%=J^I%ng}0yw&Z8c9&=V}ANs+z?L@ydh8=u`rz(^K-MQQyBFr=W-XOkk<GvXjy5+OZR5<PJw2#DTn"
    "_NT$_@pKOD13~Q-{ft<^9Kg|_ah@DE;xpbbt6!U?Ob~-pMIEbHv*Y!r_0fgDV<{3F0!zw^_C@O<jF&t?jNt;AozvmT91m#-Fr+Ub"
    "07C{RZjfYh0vX1Qv9b3G0!xo;<5Z_1Z8*^;YJ_u5#T}?fh5?<CRlv<@0rW3g913wHGJPlT{xRaY77>U{-((yzO|9n?0j&8k0{TqA"
    "pg2PW)ekW-L6eZ%GpFmEmBl^Sq!#cqO0U{;ROLO9Z@ZZ|Juvxz_-${EP1q~~7zAJhFbR$jDk6AB@G9Zb2w5YzZ+sf6h86qB363dz"
    "`I*Z+CKXKN<!4>MK*h^&LIzYNnFEEj7P96TxQJNmi>!$5hD<%H-1*99@;Y#_9))D)4~qa5X`MsmWh2a7DsVkIa<Tq$#0=TpYQ01c"
    "BkGZY01v&*L7G9Vv^*g|^klq<bBV>D4FZ1*sWxY>7d;>+K4U4r<J1G|=HeI_9QcwH?$@4|=JL0(7Wm`0AO8N!FTefe*Wdr!zu%ia"
    "<$amS{qg&~TNPV}5bw^bV`*ZG*E=7=3ln4d-XFyyEVYe~xWmH2q-<7XbsG%}NMBwU)t4t0nBB1Q7L>dZpChv&WU-C%#xms<YJ*@J"
    "59_NNeF6Dg6@7mMd!K)iJc7l>3-|B{V>i#nJh6L!TV=`yMb=L&@VGS0bDq!#LSN}TDhmSBdBlcCyCj1LIHnk@DyGR2pJ9%xH5&~>"
    "n+%eNu=&o>c)7m=J=yM=d$XSHz>MvJ#hW%R8NLg%Y{{_$Ej><ul$SWqDLkj>b9@JnZ~JOI6U$`b-dO=nl18;%Z0{V=$flB88_?XU"
    "#Hc=GLKk%$!owrmH%*x)>7<}j{a;m1uoi^IQZFwzQau}$EtUc?!6)@wT?|s408KscU1sV8v;hd}E=*T}=<2MU;57vwSixkWuFcd1"
    "gcYc(2-@gkEZ=wj6sQZ1SBJk}RWpQXK|`?g9kv_tH*{g>X5GK1j#%$bJ@h>{#3GPiP@1g3A*Aab#8F+Duwq}MN4f?SpIMixD@qpE"
    "brDu-E0mZupkP4nyZSl=lNHep9#;=SeRm=u7Rz?(I|vBM5-JZYSga}qYj;A`6$f;mQJql5Mf(+2Tp?5h%aP!-6KSvhBUVIF-Lsy&"
    "Zx-`W2*=KKJW|hHrGf+ch&5e}vznxhV3dAEl5HzPieUNzR4J4=1X2(*T}kSSI)sWNV5ms-RSI4*IMs%Ls1Hn65#7*)KthN`n^l&5"
    "G=Wyfhx&T~AyzzMCDGOTINyA6blZ`<0xb0bzcQO(Ai9!#^NmksxJ55@dHEjleSn0Z@!s|XLV_UP?%v54{w1Njpl-2^0hE!#_>!bS"
    "UJgXUf)X2>AVD^Q31hoQvigWGF;*X03Bh}?b<u4T&*fl{=5X>xD*bp=MKb*!&Cg|Lgrrl1=!s-i%=Z;<A{4ODtBrv8N;*)fzUp7l"
    "TC-y!4oe7zx|0CR5r)j|jKcRj3fkWQz9WJ^ITU*+Ob6X%0V-0AeHhGGB4X<%(A9tr2oY>0(uH;RE%LlXu44iBY~2|^l?;D}@SeDD"
    "D3+3dH+?2hR7N5UZ!^|{(eTVu%0j$AmKtE|akG*DLoRIUMXUz~B?4W2QP8U_KcRpG`6}1i(Zae&kOGDRQs3(qW<|_uD@akgnwejI"
    "Ztq~|`Vh*W3wrlOi&HSFx`Gs3P{b>=jwuUMS={?NBqNhNFhE5+52U(*k)>y^$Sy2T*$q!Dp>zL&;!9vQ;v?^i7|5*!6>};UOj)!Q"
    "fb~V9FH;O?{1(=_i>UZw=}U*a$m)>A3#@#pZ01`KXZdCN0@K&9AHV(ZKmPe2zy0^0{&C+9cVDIR{-?})a^C+>pJ{qg)3Yw07eCD#"
    "gBm|EeTmsy{P%T9MevvY%H+$^pEZ5depUP{B)=PeTKr`2%bm*eo44}v`A}bG^4ZeI)3JQ9?H#4Ry~(D%e5aRrVU*@y7WvuhH=nch"
    "Tu6T8^OHP%PUtza^zoe0b2_z`nEu4{C0)Ptuju+V{&Ids{-#lWGe1xEss7#bpTUphx!C-&_?gM)d5;>(Ut#%G(#LZ-<iGukOn*f3"
    "g*|is{t&;e`az#pdS=f>k&j3|v**(DXXzjIEAg*CCnoQg|8<;_UUa{-<#sj7a5j#sy4vHoM{5YbU|w+5#9!kW?T{FQ^CeRILPGPe"
    "jFDkLO4^tWYk{#8zbu!&gujrhpPZS<y}J>x@q3*qV(a$`VuaN`+jq_p=koquT1V>exgpSyCn;S|oYvoGZ>XMdok<l#Pd%_zKhQ%x"
    "gnoud>Zv2nh*N~-f~6`dop$P{YYv3NY)#ITDwc;$k0bt6B2}=hqH{Fs7RPP$aO9#Ml3eUH2SxLfRJV1X*Z9QetyKOn??eyMod3M2"
    "N~z1xd<i`lktzpLre>5=lJ|;iG0w$WL1eX;Xs*JaI{K(f)cH%ZE;$5Aia!&X{l=c7Bk2!vR&QKC;H>^o&jk=EtcT`w_578+L6V^d"
    "h}0$CJ5+PQKF_xm)-!F*H`=t-cEB&p3B7$Sq#s3HQqWJiE?Y2mzo!(8ZxNQ1>$@+L(^uIRkmrzK<Z9kU*^36|{hAHv*L)5Qv0eB!"
    "9{X*m<B^PL>bQw)J&&7SN45aaj9>wosaRt!bj9%$ab%QwDI!3|g+i&&L9SZH0J3s1iHiwb8-9M^XG?!s*}ll!3t!hQ`Oo?)8Ovtj"
    "kF;OO+^If1Kl2OAkIGN-x$M$E&|e<(7wx&r7bU-CBVRW1MaY*&c`bhyzpZ^-!amM_vGir8PxYrL_A1FwQS@a^pX$Gser?mMrGKuS"
    "(e%3YPv);8d%ZNt+C%L<rLF%G{$;ZEN9}X{7rD&5l4p|t%;dShiP`J^T^qjihufF@i`=A6?NywfW%-S@)tx?^UXA!9B45}u*H_6}"
    ">c!SlukG3|N{`E4*3uP!s*+yWTIeO#lIdFWrL0{?L%taPM<ah*|IpfUB>La}{P^vM-+ub}fB)t8U;oxGMg#oaePrLd`*n^4#P|7$"
    "Vtpxue8(TySLc4+SSIbBV#&e`8-Vf=mAo;1LE&ln2$pQ3c1>RX5CatFyuQZw>|!&9NneU$gPns2$~g#AU)|Wn<*`1ySXiO?SiC@e"
    "8JLg_O5Os`hr{P#2oK~<RZO2#&c2W%2|<x%-;78b8-2iH#jl+r=S@)F=t;sr+A2D}t?J{KgB@dDIs4+tjbtwnPG{xjH+InDQUd7q"
    "x1LFDVQ1k_!UDhG@KM(P%Y0_Oq+?m-wmW%wUREw&D|$)FTlRR7TXzW-({R#d<yC&$+-)vDl=|8?ZY-*oyz}uQr&<VvFP@|{Pd`jt"
    "U5O&vd4XLE$E{9CiYl~#uV`bE*1d4%C3E43^{5}DXI?@;vh;lG9Bgz20+Ek*Da3E9i{wlXgU~fA*opCtw`cdXW$Z-zEVp#1-2@UB"
    "G;WMZ_--fohAsm`e$hLrU|q^YP9)7Q!98UKQg<2z_*hhfNTAyaYalEFt($a0lq?cLh1H-WbtS@rzTD^8tw5Ow`Xxwi6AA=^mF<9?"
    "a3q8mjy>Ref3)HVG=xT>=}<uN(pW`Ab$)X12&4!GDcB?7xq2tngLI+^UbZ00P^GSV-FxP$N9S+?3(kP{f?Mx*k;p2f_~i}tfUivx"
    "u4Y+6nFOce-UJ8~B;-v9bk_9<0fmBO1zWum9Lr*sl_|**qQya+a9kI0wa8{gD!{l13_}6;0Jp9Nc?kt67;v|(L7ocwbr%{|PoTyE"
    "e0wL5{tIY^nD?wp^Xo=5tZT49vUoXOn8hzbWc?Q}4v?)D)N<r)2w3Y-pd_0Wc}aV8S8Kp^mA<Vay&KkmJcax?VMAE$inbs}3KU8b"
    "$`Xnc@;W51TvLWj!Gz?+Y!7lk$9v+s?{-dod^64NAG+{;W|dtX4)Y5ebU9KH*Ps<~7Ceh9m69-)q_N1a273i6=J0)15np+A@yp$&"
    "RL?#Yv+j3Oj^5yg<tz$2(1Y{f#O2zKXTkByvP32~fGz?CpdSJfM|||tIF8)*#tz>Ik*J(#;TOU^F<QSskGKfOJXZ=!>GDI|mFD?T"
    "8=X;A1}z3Og$Dl12*8y%?z<C8Uh=@sE6{6O$c=FkHy0`<@<0*5CurCeiu0E}JVJy^<mW#kTT_L3+z#o^(#wkPpFwxI)FbF3x-OC9"
    "x-)3WJsQ+~0DS5OuhVk%Ug}zqM*+05NDo0B#Ky0S-@Le%=2EV&xs*)^>YIA$ke3c4j4kBqJio&{zd(v&a<QG+*zi2(c_%TA$72-@"
    "Y+h7)l#fIf<%g`ZMWgM?Bahs_1vbyiifqf)P1dNajm<rSAHV(Z^WT5@-|x+}{`p+{{rI-5!yqpp=sz)xSx!PQpiFe7#kw#=Sy?(^"
    "LHA!&m(J34UAp&93gX~gERR&MEWryy3ad=-`>!h>=&CZ%m1d}aoW*rrGD8;)VTURce1Bm6px;kgmb6658$lJ@JYiwTA?Q*qDjC06"
    "#?QioqQ4QmRMz~h;rm;|tOS<w6#w5J-l1%wUo%d`x5mq)r9NhXu#_xZi&c%vm`DaH$>%+FyuTF8#Q&kINC@RzSI^^P`8B=g5cmFo"
    "^{DHT<)O#EYEa_d*CWAA9oEb7uGX{KnZ<228(d+lf?ax((2Ro7W8ikO#h_zYpO+m;!<KBAzapLm4@baH9@EEUiM|VAk;*PC>)3U|"
    "Tl%6RJARQ5=a*xZVCh^I^Ri+$EB<BLKPN0(5mu-Tf-xSpF)ks&HZsO4#juUOx<YJ>RT-SOfni?1f*<Q^OR%2!62>|cs*_<Xl40Ih"
    "OG7ro)mPz=FVW3!yC<(<N#SLMR~GO7Y4HJK;#f;YnTumN78P9VKWjmF0b`7JaUN}$G0e~17cVNjsMt-@=R{;%-V(9V0+W=WCK`NC"
    "3%KAy@4SpF2j<aOQQ01R1SSLQ(pq&>s%01}k0{a;(>-K19El9Iad95Yoyki&R+VTy_{^Fs!jdAJwy`oxNy!J+R}H&+|Gwt)HU=20"
    "ij6Ac40LGrAj|4ip|aKD-RCEgz^aPvebIPY-5@qL<;HoH^Qt0Sm3ohR4%QQS)|J=M>qLqr+(mcUJP-4%-Y(<b7-6^v9QuM&Y+RHV"
    "6@BAQP|OSL%^<MO^XyeqNiVzSjYGv4101W1V~O$t#T>@4tXFvGtx|YdVjhiixGc;O8!E<!9JLPzI2IHPB<3&KKD^Rq=<sKQCDvBU"
    "7{(P6D}hxs+%vI0tPTq171^L*pbTZ94}&Y4yfCcInFCqdxTmHNC{M%6)K^9f8iu9<rEhj(*)qQ04pcU>=?2E?T3-UM_zZYTgLz)("
    "q4g?N)+w@UEul>R9QL{8<C?RuNh46DlE~^M7b`9{rQ?vvs*+W)`sNsCaj3BhooIIioFL(eYw3G2)Q4=a98sUy#JFNs;kr=W*s`Xp"
    "oJCwMoOLmlu1jT=4_H-(u;M@$4k2AdTCA8wAyKEP7XY$A5N}~1O9`B)D&VBQFjsR5(N<~W0?Mk4)djs|d0D`%Ct=<yRS%Rx5Il@w"
    "SCon+cvay&>&uG1)k|vniek4|Jh1Xxl(<N&s=j2!hV4rkZyDM<KvnW_DYBQ6w@dN)Qr7F-*KKIBVi8;86@^#Gigi)2EM$>?Xz{Qp"
    "Ymp2C%V%4*aM?^{>xtb1%%KgJvZo!2US~!PZ5Pt!-aCc={_{_N`|B_N*YCgn$9)*@-ZZ_3HSJ$NIva{6747a(&}(35U}zT&AyZYe"
    "Pr$gqpn<BmYN&}vO{WQt90_K?hA?=UObmJ)5CJO8D0JTIeK#67l`CCT9SvA5U^Ec!(0hUk4I8}$X;?mF#2pz<DjMJOn;Z2+Z)(W2"
    "cD)rO)dj2orZLO~tiU7c#oZe6d7^^K<TC-?hM9;?r-;wKe#rysBqaA%kQNojpgiNOPV`>PxOsq#Wo&Gz<zVGtZD7%uMKFtIUVxpM"
    "C+PZHTUakx-1UEjp#kQ;5_SmYKLXaF^TL=)%%{ZEfU9SG5*-Q=1__Y~CxvHV7n^z0y(R*+SFyynw!zDf76wa!#<wNdXfkM9sEChV"
    "2J5?OI=*b?5)mzfhsLJ&B*MZjjwLe2{;Djun+<(=%ai&%;%PPrR&;&Bm!kWJF|T6x-30F&3Mi(@3SQGUuxj$8jli&aV}=cb7dNsO"
    "l8rs47n2=bHFjpcs~XtuZJzJd$&6?W*mQPgAz(ouXw3Vwe*|WYnfv+@VHOUKA8zVzUB-+W^9alXOs39stP?Yn#>AkfVA_M3fC)LD"
    "kn<A6%*>ecw?q&#I1PjarXd~z0o!MbArkS7z=CuVFe5M#W){q(F&hZNP-e`mSsyMvi>rpRCZ4<a1hdA>C`T&j&kU)~WAUsxzp<|P"
    "nU1V;ok0^1rlF)6N}8W0Q{+7{LrD`)nm7Vg>q#0)yU_Wq^{myp#K1sGvsbXO`!aimaY~PL7vor4@2nO$HcUvrq=FX#`zOg4>8LrF"
    "xVYDJV(~wLS@~NgJc6pY038#*xXv$F$1l^V6ThGd(`(>(Ycp|bXpR^(3<<MQgy2yukyv0GV+g@zH7s@v5C#g*DI=dMW#?!J(5Q*$"
    "1COMDjkr#+%4`s<j~r9S9K$Zg%L*11*~mt~7;}9=F!h}U8*4LzY+%4-DV8}lc0zL7-<y&g$_zp~D22)OZKpzZ4~i;Q(X>t#%VNJK"
    "BSlmUPvDYdb%^bkRWuK-)B^-D7FLBIi<KqoQLv(wfu*Z3!6I2qS43Zc_mzjJvnpaK(1oBvpi4rvT{=0}HHa5pr7dL*@|OO@7Kb{d"
    "u&}Oskxjv}fzfp`PVB2!MG-D@MQ^O1I-OVvajbGVAr5F0G+~br7q63nSboKNBhl+rANuxZ6yU}E@|YRM0%QXv^WsdphCM7L;i^Zw"
    "dl4_HLfxXl;1-ozw%jmKk5~PJ;6~L4f_l6X?}gsIwd(;z`w3st;AP&3-hjU6A-f+FB^ugV_Ko754iG+I)E}V!ftwXB-ISsl2pYKF"
    "@POuj5f^(lP*7313rF=PbZmj5QbRI5qZ$I^g4~|eeF*ASW>7uzL+@ULtPi?|nG3Jx*wk=_{`l>Ozy12teZCXk>+sO#YH=MVP4_RU"
    "rS*$&lh=QRtsm-7{FmMu)_7@Mav3q!XQT61-4I4>a2~~yjwNm*9m=wNFrJ33ys=-!(`1W<<t;C=U%*7XAoSJ#>y`o&zq}WeU(XZ2"
    "tO!-{xzb<l3zohrf8nt4BK4&%EErf|vRfX)&>?EcD-`2Din_&$at>eTksspJc%bOh&iaFL$a`Tcze_gq9{>e$+3Dcn`w7azJn>KP"
    "<YmhA){1f0sk|2<(>np&{CU_&u8kN)gl=re>TRmhYEmqGgr!655842Qci-J{Q3SKlH6WLAMXIBiWG&<cLKV6J2qE*%OZOlspr}FX"
    "S|rP$rRiCY>yBGa5grj_RCRP|7KW0>BC0->gRwV)eq7$rUZ*PmWG|xMgSV9@3{@$psIQiKRTqVV35AW|HPr_$=m{%GL9YIY^**5y"
    "s6_^id%+MiZg`DLSMDcDx~pT_;yqzqlr<&`l;y_>qNQs>kqJh^8c;N$F}ax6G$Qp`vdX^}svQd7#w21wUW3M<*I$x#N%bZxVW@N{"
    "5GXCdgrUaDGDBGkW+_-!hLU8xok)X~r>+yo6wC`swqX9MMW#MKI`J0F5<2nT6nxf|WgaJ#NbC`Gu0C;HUh48&^-%^V%50}uR~5nO"
    "7u8jkAZKwXS-LjCVd{lNFIiuPn#F`WD*=tzC)z}XV5<OoU8Dy{v&T#bLV{6x{{a-qTS0*W?a60f7*vSs3dH*$UnfW~VV0k7zDOY="
    "xPg!$NY=QkyIJ%$i#q{$q~QH}ZxcZR!G*7p_v?+ku9=<hZ8z1AWdsIADd;5xRM3DN6^s%JZ45Xs45h=IrRt)W_y=)4X&~2=YEm#c"
    ">rVF2w-gH2Q}8XGH<ASB5%K-9!zz%XAZ`L)PzdsBgFYhFFBL6lmLTr(1ZD^QW<zdDnTQu6UWf=^J=d}B(4-<ymy8y4m!~BH{E|_2"
    "{U;U)XChhZ0D8$NRvP(5l95}9bj3jcQ^ZrCs*K#{;u{K8GGwsUY={J|G|*Ka3=BsIa<5Q(w%qfGgmnYzTwel&WQ<&WosisI8V1Q@"
    "XlNRD{R*g(H7-REnBZ!Om=)xD*%=fK=;~{i4a#hZ)6ZTmBIshSuAUF;>isN^*J5!9FM@W#_zWq2VHSZhc9rQGZ;34yr)WCUmi8Hd"
    "eklT3JMI`39TR7XQRl{MlkhzD_?aixv1jZO!4h8s=Qbkq`Om}hS9y`|-*8?!(3cFmsg2aq=r4qS3CX&R-3>3Y*eAn3UPkd#eNM^m"
    "fxggwaqyRa|BwIi&!7L}ufN>;W^E+wXJyHAx4G@%-eA$dIQMy55(gJE&3*U|j?co{mi-P42#gvi{hWs4`o>LXa-D@cKX=yPDMuKT"
    "@w5UW4TUW;q9_H;dSF5Bzq6<?qZaw7S>J>4Njw=Y$>L}ePY^Ce3<~B9vL*f<bd<@#w8Wj3Bd6sZXpR!{Q)LEP9H0dR4h%(RXnZ{_"
    "#d$!Y7P=wcbkZH+14Gd?6g4K#I|ZX)dV`5|24=|5uO?8A0%4*TfDjj;$xQ#H%#Uh_8u>rM3@6srGD=!$Cav5>J9_NF;#o6Hw)38T"
    "L6J_{5d!_b3rc3&ELvw(7;`K<$PSRVO~KrYpEIvN#=ID_YRtM8up~2VnOpG%M#KbzNnE<t#@AvB5HkbrZP4}?V|w;Nxz?`OH00e{"
    "wVdJ;3>p&~!dqdB32SM0F+BnMmlkoY3or4qew}TJUu%<RG6N{g5IA#!7tK+KYxjyWgHxD+l~EYis1oa`-?vJ{Q~y0fVkq}tAq)b{"
    "8pt}U$s{`8p$j}90*w9UMPg`zk(N=oc#ft{Q1b3Cqd15mv|YMD$E(dOVxD(Z95m1?6-*cRnsv{schHy^JZIuo{AY=uyF@@RnNiaj"
    "wPtu^=paYfB{n496h}PKsfvRp4kj~b%wRM9T!-6=OF#e1z^FCYBj%Y-f1uOt!Jw69;;ndem87@v<CfWrftS*Q-FK7nzAie_D+bgn"
    "CJl^=bsbbYRsYn}`qBBTpwr$RN6e%}N$t|p3bLcj%9xSApeM7S`O!G7OG<NA8xBTZ8N5|PDCiNB7l%`-x4$&7tY3<r;yx+u-HST!"
    ">1Rj_v`1EaF-HvcJo+X|1-$@)`YA`M<512H^m}IJ<77W3BbNbstTU`{)Kn10lK%KUm@-umh`0nj*@e)sLT%TD%>pW17H!VrrMk>z"
    "J;$1jr0_Hht(SPV%d=*)1}|)6vCrC?OyqG1y1qbUqk`GKc!g(TNs&#@vcT<zZ%)#j)aHm_oPx>H#aVvC@{;9utiV`_Rwhsa1Qsuw"
    "ykPQzVk0~j%(SavL9vlmP{OEmNwJY+@EFgQjh4QkV3GQ)ZEIvjR$Ip|iqDtg^Ef;}`%NwS8!&5KWO@Qs@o**{$;pQuxO3i{U^b#8"
    "UCP=!V+KBM^6oW1y{1#EygC@Q(zKa8$WilCtLhu^tcm}Lp#L09Cx-Gdc<wwEhbLw_c4=QmczrfKmAe%8V%uqB=mZQ1{PEil|Mt_*"
    "KmYZ;k=uUJ+qF|7zRchFW{9JJlR%ewfyT-6=e@rH2HGzdb4rs*L@z?zGL*PbBzh^wQ4UgrkmgL7zpmY70#_2ah!<LglKBhbSf&GA"
    "2K}Ts=L{`?h1@v2J=ES>Y|7B;kez1yVi|(<VdU^`K!UTfEg01VhTejGd%+`x0R|&;Miyp1lu;RJ{K)o*{h~N7<FE{7*Z_>kC+>+2"
    "m}VlcCmR{iJRwTpM602MH``MsxC_}vU_~A`TGJ6Y&;gHtLzPnpaP{q->S`23qz(pf#;m><S8{O~0=&kZ#aIRdtEceqkH2C3AoAGl"
    "8PMpa{QJ9pH(7B&(0@33e97-;EoO*c#{@#RzK$1!CDo6YV3*2(rdU~|E>_#p6msZl$TA<?Kt>n0kZG)~>sBo02?7gQ`3P}whN8Xz"
    "hs64CQX$pFM%)O0TXDpswyp^nfwlm-j4{No9~4|+Y(E_sP(WfD$doE=5fmY{EubP>7eU^WD`=Zki<5lY%Ytb=-PSAeC*@&l_>;=e"
    "JUQLgdQW9XI50SIE44IFpL<SW`J4&z=Fs@S$VI^U3Iv&XCmb(0Zj{&LIL>Kt_86%I@dANSf`E}s5RZ{rrm@vJju1VQGm*XryT&-<"
    "=PnTff&)U28yvuh$D^nAlVTT=YODC@6)>6(1w48uwBI-+<DSKtNWqAda%1}f53vwJICb^M7-)=S07wZ&;DDnc@Q46G{DD-fa!(u<"
    "3dG66Ru-B^NEfFFJw<S;(7fY7J3lkGp8U=5tG;yvG-TA$uGu3bsK~8({+#Tz75&uH{b}u}9f9f`^u2>XdcNk*ATG@baT>BVng~Lq"
    "s^CcEnwwx9Nse<SGBvlJkVp+=al+bOYsar9GNX~u=Nlc#9r05t3r<9cU$$m^Lif4tk98!j4=V;z1(LakE%JcNE6!+i4`)qSdK^b)"
    "t((!n+oT;Ss6IC&@m!!SzJY|bzt;`~2CpNzNi_rz()5hqTb|b2U@Rd$ZNQe0o_WG{=3*YOZBp~>X+K)kq>_+Ar$svlZRp_>@c~Qu"
    "wLOS03m_a2dK^K5hRm(MsTuG4^|P4effEpCN#%9)lOaora>6>P&?Aq|I3TGcq@pRsI1cLx1VLv{kW?_GR=&K@<AszLnxz!1olKRp"
    "m-31phoq=x5V@dIx<4Rtp>uRS{voFp;tp&*Bh32jZS;r*p(hYM8%{;75&~Jq1XK?fk_0CmaI)agl}tdp=#Nr_Qv|1OIdH(y^q{rA"
    "J~Ty(32U%ARtAu*OK85-)dNgHYT7>(Su2`!r5AX%#>sa#Jf0`ofg+j^LV}PAV#!+~QDj2YFdy~h>hTCf4Wl4;5)Y}UgAAE#=LRwq"
    "XYNhL5#6oqGsb4a0K|3xe6*>6C{-82?wwP1hJ-JtGGzB+&l$*%-+uV{_y6aw|M<&4fB*Gw@7<T+$BO3|+=RJkF;=yLAGeQ5$ZOCT"
    "Ifc**V3Fqf6hdBobr5Mf@E{DwsisM)LzAl8KWAm*Q?)el>=OIc%A27FNx`R5yKGPwrD_nWK{fUYQ8njhqYI#z!#-8w6A+SnaMN3E"
    "ejzJvxSqEhO%Lonl)+XJIH*N_pD#GdJDk<nZEXzSP&q%<YS?K8#n$w>p0*CNZ9cYNc<3#Hn)i*K%aTHMj3QGip6h8*ol;InNzF5c"
    "*p~m6$0o#r5D6HPQ09pgLXw4e1L^DXNU9_7h!jgtL;T=OpM6{3N4C7sgE<U&(sN;{Fpw$rMxw(pj02fc7+EWxRO&`>cheAD5f$X!"
    "wZ$M1+%WDnnivFv>jpt!u1iKz?xi6pUpFTUDN;Ju(Bt}mq#?81V_$oUvy{jBR4hYt97sh2n|q~lAyd!AImuyLHv-6?dvz?$E-CgE"
    "v=k8M-m^)w$%VetlV-lYOO+eRqfFn|IRTQoIn@izf%}uX&nsU^<o#YNT=AJm!qK=$nU2-N=mp|1Qd$ka=e-!JC>w2wG2<Yn(FIT>"
    "@<6XXJFJZzgao`HGgsMgnT|^=m(aLK6CvZI*eVR@AL}ngZ3?@Fs%Y(NX#zCE=}5o51C2`|;aLw_Pe8`P`Uc>&E-r()rx4I;2J(7A"
    "K%hdPb;VX+{6{3GkuZb<H%M+Mx~PzsdOVf_Nup3)s^>+s%<BtLfP5~bM;6b=yQx5nXs#JjD9!Spf|)|IN~AIAo#!DkcB+2^z!97`"
    "@5nygsJ3BFr^f;^8cmP-&*oF(u;}!tjcYQtHjZ>I<mwF@y>kFTZocs%U?jFa<HcWa5#^-4bP`5N>!1*FwN7lQzPsz>5NCAG2nnsj"
    "L{g!3yquGT9>RgqT>~~AR+GK`OMcb828@aJ*#1bcbV#7At{a8nLX5n+a<|^;1zADB+EIy_Gf-Yyfe0WXKY|Jbq|`TH*2M;RB+`M!"
    "fH7nlW_Q4<adE5`&7mV|@uQk99c~TF+}z`_0GN9|8e=uRy2h0R01hn21W>S!2_())$T0-C1;kYhKCb~dnzBS>MKH+MBSeQo`&&1I"
    "SP5LmDE-;T1g-<Mm&F*FOY8NHba-SXVI7R&s15=E8xIhrQ8f#zj!C5vb+d4c1PgI$|IH}AU!zL(PQ;-=M*Y2jDFLmh0HwISyUxgf"
    "q@Y*{?=;G@B@J;r4!jJU@`8MH*rI4<pyo1I#k7l_QMO7A(ZdOP229HRK6ccQSL(P3jM27|kRg;vDE>qX=@~cz+d8l7^}1fg8Cd>m"
    "Lb_f@m&|3BJf)y9ShjM2#$cHsL6yq7lo#VY;_?o0dye6cvo{bjQSF5yWr?3Dk{sfqT=JEg$A_ziv2w6v$aWaQ)85GQjs`(~{Px2y"
    "zyJEzfBfaIZC~d71?2meyu!Q$y&+K`>02bo`?s&+jss0kL!#issb^TnoS<;V4e3L3;{>565Iu<@&AK<G7UG3JUg&}DkCa*nh+Igi"
    "g+$CDdYs4?2*h!zd)7y-+ni!cF(mgnC&>jua+ji<iF7^fcPGn6&yXs@dU@a^RdW`4ve1)-hgs-Jy3~e4krAKOnzAAl4O;_A8(Yzo"
    "TACyAXCj_UxnU}P!Bj)ADQZ03?&#Ty1W9%XWhR6_q9i=m;yEL5AaSL+{j%+16kaDTUfITP`7X-+JF`>ExDb^|g;8*$Vnb}US0mCn"
    "w4pTwH%~~s=|SQRA2N>bKxWB#H#wtY#K`J)pddX6!Cf3wl#6k~Z`B)w49(*UnM68akL%X_9%ktoAE_)oV-+=%7n%1%YX0y^z_}Pd"
    "zOwX;<+-JYB58aTilaIX?I5YKU^kI47VKuk+83x7@-U3ArI*xL)SDiLv4WQ-C-w!r#Tgg4Ej{D*wq<K9=`DY1M`q;1Smc|WwkP6H"
    "G-6+rS+-(d*;)R?vBWn^F!nX3RiE!Kk0Y*!_eMd)HLC3|T$t0B*%or|ZY13LQ{OjPul_Wa_@;;Vci0J+*ZtLX!gV#ht!G?1ZP%uv"
    "m+yV5Ct;r(g5%tzaBaCYzZV$GkebNi^gSc)VXzRCFA|@Kkg%eGORymhb3BjyL<;3p9A_XUIFXt6GWL}+mU4&_W+@ZSL{?4cJB)}^"
    "W*y^5^SKNp3aKch;+a&L`Jz(XI^v|gp1jq}^A%OiCwj_(haVyNoOA!ed#nVh0^yvvlPXy1B1lE`rwUv3)?AT?3mKX#t-S?v#>Rw>"
    "+_qBRSw;vTBu?br1{X56Gg>aLfp`mPQnB|5%a%kE>3=xVIJx(kGxDvE>hF|0&ZIwVdJ00ChpG3gm3ml3E@tGf5smxZ6ws-dcP^$>"
    "?E5E6Di#vwt8XJmY^%MANGZozS99m|-Hh*?fk1!9t@`8odvMxn@6!wU6UJ`%v_9X$Q_p-;PwVadp0MW7-}p;UKbeU*W8|<9n8?sP"
    "#w3&D$0?nr8Roa9v-*NVH|91U!J*&Rd$aPbYTTDNot(e7hBS@eHLFWgm{1~+Cy?(Da$$Usy>c@~m&=8*k^Q#U+#I9b$$>u9o@&~l"
    "IW$|hP#bDvQ#W#95APv+9hN4Nu}}vJ0U|1)d;Wkc`IrvPFpo*zio=`;HqL^Go`K9jAjIYbgmh~+)azom<_QbSE&INUt&I4|nYul4"
    "sp|$^6Y<gu4v4$~vX&K&FxKrmkvGt-d7QT$C+|5y*E6g;ku$v3B%GdEbHqN$Eh=1)Rf)Q(uyj9hez#@f^|B?%%$?2&!XGdE@xq^A"
    "*4mxsptmgiYOq=s$weYkdV7?dWO6Lcb*y(0sVp>SAyq_9i;yZpsv=u)A(CTA#g1I0ZeV0-798)mW>1?!WoxrsDmKju2Z;58R*$DY"
    "p4R6=R-tp}coLs7R<ntRtM<mOhpviKBno8s^Mn+!+JA~9p*f29;CGPJ6PO--hvL7EBX?D_oIdZo*t;`7e*57cfB)^b?|**!{ck_r"
    "J38>*Cu+a3+19_;bN=vo$w%`1f-fq}OF{fV!1rhWA)lvvk)D`*Qq!0HPx-pNpz`lcy1hcnp_Lww<s*3p>Of!$t>?uDBZrM2CqFWN"
    "H2A>y?t$+P`GMH?^O>f{>0e;^4b1;w=s)FqR-m5bXQYQ!Kz=I7gfIkvWe}JHz-ok3)4BX|a3_E7SUXgu?vFo==aGRIutqfj(1CvK"
    "F4oxrq(cCKD-B#J2Ku+(T!{%xt%++jfvE#`Qq6AWS_@ZFSjYC_ef_I)9Rj$x(u*r?BYaX4P6TN}tNeiG$RlVP18*P>DGD8d4HAiz"
    "pId@%wV4I2N|%MA8@Uir8n6_X#prq~r(9fZ8~0tPW&*b37qFt$Mr##O0tUhYmexBA1u-IKjE@dq1pyh0Odw-N%0kxXFt3cvAmFvW"
    "b$unImMHOyf$Urh5tQ{6?kh?L=!|h0iv)rWyg;Y)DJF24m0?K%tYmy-{6cTpwzT#_9a!j}fH)3t8Qi7$L5UP_LT1?s+)f~N#+TSm"
    "GTNAdiL7t8sjpZ^;J#x*#8x%O9(24sE<V2yhvRGjVU>+k0=)QG*#upQrF9|^Q$+s!4gfPGQD%?UG%HA71oV*j!;tKBD2)%*64*51"
    "kAPiALA#@%^ewIT5kUGJP&!uzlpP~uM&v*^0uq0hWDX=1xYkT?zHT_uUTf>?<oPCy92n=1B!Gtm{Zl!NIE1W&b+3C_ahT#zn4g)!"
    "@~3|=h6f;cSOxQ*DLUGbND`XIJnO~BEr6jw#@10F0S%itG6vLf4z{o!5PBrysE<*FE-rSl`9~jTdJBjH2rH-sF<^~%Tb9s>IG|u<"
    ";acW#NZd~1cKG!86}hjGh{Q2V=yoOI7J`e`bIYFV^`gvl0A&YOP%@f}ky^&gIHuH*(xcCSW`i$2J)D^(08AiG75a=ePM5~>RN%Qy"
    "&zuT|hLMSYHR4JAG{H4Q=A#gZ6reshp+OOdmdcT<wA0`aVTL|24Utul#7(9LlZJ)BeF#qyii-UbSl~{!m;U=Xvs`6f0|lTvDNLX?"
    "oLRHr9R(9u3yq4+sAyyY8x6}Q_vt}n<Qf$drW0p2<ChnFow434R+I~WO&biDE*JK$6#~@)+{5#X5+5i$XpG;ky@m&q3vi}@85T88"
    "?fJ+5_x}Ue&%Ku"
)

_TABLE = None


def _load():
    global _TABLE
    if _TABLE is None:
        raw = zlib.decompress(base64.b85decode(_PACKED.encode("ascii")))
        data = json.loads(raw.decode("utf-8"))
        _TABLE = {key: [tuple(row) for row in rows] for key, rows in data.items()}
    return _TABLE


def lookup(
    country_code: str, city_key: str, target_date: date
) -> Optional[Tuple[str, Tuple[int, ...], float]]:
    """Return (method key, per-prayer minute deltas, altitude) or ``None``."""
    key = _CITY_INDEX.get((country_code.upper(), city_key))
    if key is None:
        return None
    md = f"{target_date.month:02d}{target_date.day:02d}"
    index = _DAY_INDEX.get(md)
    if index is None:
        return None
    method, altitude = _CITY_INFO[key]
    return method, _load()[key][index], altitude
