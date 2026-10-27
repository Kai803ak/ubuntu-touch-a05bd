import QtQuick 2.4
import keys 1.0
CharKey {
    property var composer
    allowPreeditHandler: true
    preeditHandler: composer
}
