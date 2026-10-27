// Romaji table from ibus-anthy engine/python3/tables.py.
// Copyright 2007-2008 Peng Huang; 2010-2014 Takao Fujiwara;
// Copyright 2007-2014 Red Hat, Inc. GPL-2.0-or-later; see COPYING.ibus-anthy.
// Composition logic for the A05BD port, GPL-3.0-or-later.
.pragma library
var table = {"-": "ー", "a": "あ", "ba": "ば", "be": "べ", "bi": "び", "bo": "ぼ", "bu": "ぶ", "bya": "びゃ", "bye": "びぇ", "byi": "びぃ", "byo": "びょ", "byu": "びゅ", "cha": "ちゃ", "che": "ちぇ", "chi": "ち", "cho": "ちょ", "chu": "ちゅ", "cya": "ちゃ", "cye": "ちぇ", "cyi": "ちぃ", "cyo": "ちょ", "cyu": "ちゅ", "da": "だ", "de": "で", "dha": "でゃ", "dhe": "でぇ", "dhi": "でぃ", "dho": "でょ", "dhu": "でゅ", "di": "ぢ", "do": "ど", "du": "づ", "dwu": "どぅ", "dya": "ぢゃ", "dye": "ぢぇ", "dyi": "ぢぃ", "dyo": "ぢょ", "dyu": "ぢゅ", "e": "え", "fa": "ふぁ", "fe": "ふぇ", "fi": "ふぃ", "fo": "ふぉ", "fu": "ふ", "fya": "ふゃ", "fye": "ふぇ", "fyi": "ふぃ", "fyo": "ふょ", "fyu": "ふゅ", "ga": "が", "ge": "げ", "gi": "ぎ", "go": "ご", "gu": "ぐ", "gwa": "ぐぁ", "gya": "ぎゃ", "gye": "ぎぇ", "gyi": "ぎぃ", "gyo": "ぎょ", "gyu": "ぎゅ", "ha": "は", "he": "へ", "hi": "ひ", "ho": "ほ", "hu": "ふ", "hya": "ひゃ", "hye": "ひぇ", "hyi": "ひぃ", "hyo": "ひょ", "hyu": "ひゅ", "i": "い", "ja": "じゃ", "je": "じぇ", "ji": "じ", "jo": "じょ", "ju": "じゅ", "jya": "じゃ", "jye": "じぇ", "jyi": "じぃ", "jyo": "じょ", "jyu": "じゅ", "ka": "か", "ke": "け", "ki": "き", "ko": "こ", "ku": "く", "kwa": "くぁ", "kya": "きゃ", "kye": "きぇ", "kyi": "きぃ", "kyo": "きょ", "kyu": "きゅ", "la": "ぁ", "le": "ぇ", "li": "ぃ", "lka": "ヵ", "lke": "ヶ", "lo": "ぉ", "ltsu": "っ", "ltu": "っ", "lu": "ぅ", "lwa": "ゎ", "lya": "ゃ", "lye": "ぇ", "lyi": "ぃ", "lyo": "ょ", "lyu": "ゅ", "ma": "ま", "me": "め", "mi": "み", "mo": "も", "mu": "む", "mya": "みゃ", "mye": "みぇ", "myi": "みぃ", "myo": "みょ", "myu": "みゅ", "n'": "ん", "na": "な", "ne": "ね", "ni": "に", "nn": "ん", "no": "の", "nu": "ぬ", "nya": "にゃ", "nye": "にぇ", "nyi": "にぃ", "nyo": "にょ", "nyu": "にゅ", "o": "お", "pa": "ぱ", "pe": "ぺ", "pi": "ぴ", "po": "ぽ", "pu": "ぷ", "pya": "ぴゃ", "pye": "ぴぇ", "pyi": "ぴぃ", "pyo": "ぴょ", "pyu": "ぴゅ", "ra": "ら", "re": "れ", "ri": "り", "ro": "ろ", "ru": "る", "rya": "りゃ", "rye": "りぇ", "ryi": "りぃ", "ryo": "りょ", "ryu": "りゅ", "sa": "さ", "se": "せ", "sha": "しゃ", "she": "しぇ", "shi": "し", "sho": "しょ", "shu": "しゅ", "si": "し", "so": "そ", "su": "す", "sya": "しゃ", "sye": "しぇ", "syi": "しぃ", "syo": "しょ", "syu": "しゅ", "ta": "た", "te": "て", "tha": "てゃ", "the": "てぇ", "thi": "てぃ", "tho": "てょ", "thu": "てゅ", "ti": "ち", "to": "と", "tsa": "つぁ", "tse": "つぇ", "tsi": "つぃ", "tso": "つぉ", "tsu": "つ", "tu": "つ", "twu": "とぅ", "tya": "ちゃ", "tye": "ちぇ", "tyi": "ちぃ", "tyo": "ちょ", "tyu": "ちゅ", "u": "う", "va": "ヴぁ", "ve": "ヴぇ", "vi": "ヴぃ", "vo": "ヴぉ", "vu": "ヴ", "wa": "わ", "we": "うぇ", "wha": "うぁ", "whe": "うぇ", "whi": "うぃ", "who": "うぉ", "wi": "うぃ", "wo": "を", "wu": "う", "wye": "ゑ", "wyi": "ゐ", "xa": "ぁ", "xe": "ぇ", "xi": "ぃ", "xka": "ヵ", "xke": "ヶ", "xo": "ぉ", "xtsu": "っ", "xtu": "っ", "xu": "ぅ", "xwa": "ゎ", "xya": "ゃ", "xye": "ぇ", "xyi": "ぃ", "xyo": "ょ", "xyu": "ゅ", "ya": "や", "ye": "いぇ", "yi": "い", "yo": "よ", "yu": "ゆ", "za": "ざ", "ze": "ぜ", "zi": "じ", "zo": "ぞ", "zu": "ず", "zya": "じゃ", "zye": "じぇ", "zyi": "じぃ", "zyo": "じょ", "zyu": "じゅ"};
var symbols = {"!": "！", "\"": "”", "#": "＃", "$": "＄", "%": "％", "&": "＆", "'": "’", "(": "（", ")": "）", "*": "＊", "+": "＋", ",": "、", "-": "ー", ".": "。", "/": "／", ":": "：", ";": "；", "<": "＜", "=": "＝", ">": "＞", "?": "？", "@": "＠", "[": "「", "\\": "＼", "]": "」", "^": "＾", "_": "＿", "`": "‘", "{": "｛", "|": "｜", "}": "｝", "~": "～", "¥": "￥"};
for (var symbol in symbols) table[symbol] = symbols[symbol];

var prefixes = {};
for (var key in table) {
    for (var j = 1; j < key.length; ++j) prefixes[key.substring(0, j)] = true;
}
function convert(source, finalize) {
    var s = source, out = "", i = 0;
    while (i < s.length) {
        var tail = s.substring(i).toLowerCase();
        var c = tail.charAt(0), next = tail.charAt(1);
        if (c === "n") {
            if (next === "'") { out += "ん"; i += 2; continue; }
            if (next === "n") {
                out += "ん";
                i += tail.length > 2 && /[aiueoy]/.test(tail.charAt(2)) ? 1 : 2;
                continue;
            }
            if (!next) { out += finalize ? "ん" : s.charAt(i); ++i; continue; }
            if (!/[aiueoy]/.test(next)) { out += "ん"; ++i; continue; }
        }
        if (c === next && /[bcdfghjklmpqrstvwxyz]/.test(c)) {
            out += "っ"; ++i; continue;
        }
        if (tail.substring(0,3) === "tch") { out += "っ"; ++i; continue; }
        var found = false;
        for (var length = Math.min(4, tail.length); length > 0; --length) {
            var part = tail.substring(0,length);
            if (table.hasOwnProperty(part)) {out += table[part]; i += length; found = true; break;}
        }
        if (found) continue;
        if (!finalize && prefixes[tail]) { out += s.substring(i); break; }
        out += s.charAt(i); ++i;
    }
    return out;
}
