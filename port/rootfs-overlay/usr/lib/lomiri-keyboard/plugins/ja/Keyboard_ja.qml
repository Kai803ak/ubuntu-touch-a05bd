/*
 * Copyright 2013 Canonical Ltd.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; version 3.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

import QtQuick 2.4
import keys 1.0
import "keys/"
import "Romaji.js" as Romaji

KeyPad {
    id: keypad
    property bool latinMode: false
    property string romanSource: ""
    property string lastRendered: ""

    function syncSource() {
        if (maliit_input_method.preedit !== lastRendered)
            romanSource = maliit_input_method.preedit;
    }
    function finishReading() {
        syncSource();
        lastRendered = Romaji.convert(romanSource, true);
        maliit_input_method.preedit = lastRendered;
    }
    function onKeyReleased(text, action) {
        if (action === "commit" || action === "return") {
            if (!latinMode && maliit_input_method.preedit !== "") finishReading();
            event_handler.onKeyReleased(text, action);
            romanSource = ""; lastRendered = "";
            return;
        }
        if (latinMode) {
            event_handler.onKeyReleased(text, "");
            romanSource = ""; lastRendered = "";
            return;
        }
        syncSource();
        romanSource += text;
        lastRendered = Romaji.convert(romanSource, false);
        maliit_input_method.preedit = lastRendered;
    }
    function toggleLatin() {
        if (maliit_input_method.preedit !== "") {
            if (!latinMode) finishReading();
            event_handler.onKeyReleased("", "commit");
        }
        romanSource = ""; lastRendered = ""; latinMode = !latinMode;
    }
    function confirmOrSpace() {
        if (maliit_input_method.preedit !== "") {
            if (!latinMode) finishReading();
            event_handler.onKeyReleased("", "commit");
        } else event_handler.onKeyReleased("", "space");
        romanSource = ""; lastRendered = "";
    }
    anchors.fill: parent

    content: c1
    symbols: "languages/Keyboard_symbols.qml"

    Column {
        id: c1
        anchors.fill: parent
        spacing: 0

        Row {
            anchors.horizontalCenter: parent.horizontalCenter;
            spacing: 0

            RomajiKey { composer: keypad; label: "q"; shifted: "Q"; extended: ["1"]; extendedShifted: ["1"]; leftSide: true; }
            RomajiKey { composer: keypad; label: "w"; shifted: "W"; extended: ["2"]; extendedShifted: ["2"] }
            RomajiKey { composer: keypad; label: "e"; shifted: "E"; extended: ["3", "è", "é", "ê", "ë", "€"]; extendedShifted: ["3", "È","É", "Ê", "Ë", "€"] }
            RomajiKey { composer: keypad; label: "r"; shifted: "R"; extended: ["4"]; extendedShifted: ["4"] }
            RomajiKey { composer: keypad; label: "t"; shifted: "T"; extended: ["5", "þ"]; extendedShifted: ["5", "Þ"] }
            RomajiKey { composer: keypad; label: "y"; shifted: "Y"; extended: ["6", "ý", "¥"]; extendedShifted: ["6", "Ý", "¥"] }
            RomajiKey { composer: keypad; label: "u"; shifted: "U"; extended: ["7", "û","ù","ú","ü"]; extendedShifted: ["7", "Û","Ù","Ú","Ü"] }
            RomajiKey { composer: keypad; label: "i"; shifted: "I"; extended: ["8", "î","ï","ì","í"]; extendedShifted: ["8", "Î","Ï","Ì","Í"] }
            RomajiKey { composer: keypad; label: "o"; shifted: "O"; extended: ["9", "ö","ô","ò","ó"]; extendedShifted: ["9", "Ö","Ô","Ò","Ó"] }
            RomajiKey { composer: keypad; label: "p"; shifted: "P"; extended: ["0"]; extendedShifted: ["0"]; rightSide: true; }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter;
            spacing: 0

            RomajiKey { composer: keypad; label: "a"; shifted: "A"; extended: ["ä","à","â","ª","á","å", "æ"]; extendedShifted: ["Ä","À","Â","ª","Á","Å","Æ"]; leftSide: true; }
            RomajiKey { composer: keypad; label: "s"; shifted: "S"; extended: ["ß","$"]; extendedShifted: ["$"] }
            RomajiKey { composer: keypad; label: "d"; shifted: "D"; extended: ["ð"]; extendedShifted: ["Ð"] }
            RomajiKey { composer: keypad; label: "f"; shifted: "F"; }
            RomajiKey { composer: keypad; label: "g"; shifted: "G"; }
            RomajiKey { composer: keypad; label: "h"; shifted: "H"; }
            RomajiKey { composer: keypad; label: "j"; shifted: "J"; }
            RomajiKey { composer: keypad; label: "k"; shifted: "K"; }
            RomajiKey { composer: keypad; label: "l"; shifted: "L"; rightSide: true; }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter;
            spacing: 0

            ShiftKey {}
            RomajiKey { composer: keypad; label: "z"; shifted: "Z"; }
            RomajiKey { composer: keypad; label: "x"; shifted: "X"; }
            RomajiKey { composer: keypad; label: "c"; shifted: "C"; extended: ["ç"]; extendedShifted: ["Ç"] }
            RomajiKey { composer: keypad; label: "v"; shifted: "V"; }
            RomajiKey { composer: keypad; label: "b"; shifted: "B"; }
            RomajiKey { composer: keypad; label: "n"; shifted: "N"; extended: ["ñ"]; extendedShifted: ["Ñ"] }
            RomajiKey { composer: keypad; label: "m"; shifted: "M"; }
            BackspaceKey {}
        }

        Item {
            anchors.left: parent.left
            anchors.right: parent.right

            height: panel.keyHeight

            SymbolShiftKey { id: symShiftKey; anchors.left: parent.left;
                width: panel.keyWidth; height: parent.height; }
            LanguageKey { id: languageMenuButton; anchors.left: symShiftKey.right;
                width: panel.keyWidth; height: parent.height; }
            ActionKey { id: modeKey; anchors.left: languageMenuButton.right;
                width: panel.keyWidth; height: parent.height;
                label: keypad.latinMode ? "あ" : "A"; shifted: label;
                overridePressArea: true; onReleased: keypad.toggleLatin(); }
            ActionKey { id: spaceKey; anchors.left: modeKey.right; anchors.right: commaKey.left;
                height: parent.height; label: maliit_input_method.preedit === "" ? "空白" : "確定"; shifted: label;
                overridePressArea: true; onReleased: keypad.confirmOrSpace(); }
            RomajiKey { id: commaKey; composer: keypad; label: ","; shifted: ",";
                anchors.right: dotKey.left; width: panel.keyWidth; height: parent.height; }
            RomajiKey { id: dotKey; composer: keypad; label: "."; shifted: ".";
                anchors.right: enterKey.left; width: panel.keyWidth; height: parent.height; }
            CommitKey { id: enterKey; anchors.right: parent.right;
                width: panel.keyWidth; height: parent.height;
                label: overrideLabel !== "" ? overrideLabel : (maliit_input_method.preedit !== "" ? "確定" : "改行");
                shifted: label;
                allowPreeditHandler: true; preeditHandler: keypad; }

        }
    } // column
}
