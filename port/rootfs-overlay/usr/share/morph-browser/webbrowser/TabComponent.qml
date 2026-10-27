/*
 * Copyright 2014-2017 Canonical Ltd.
 *
 * This file is part of morph-browser.
 *
 * morph-browser is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3.
 *
 * morph-browser is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

import QtQuick 2.4
import Lomiri.Components
import Lomiri.Components.Popups
import webbrowserapp.private 0.1
import webbrowsercommon.private 0.1
import QtWebEngine
import "../actions" as Actions
import ".."

// FIXME: This component breaks encapsulation: it uses variables not defined in
// itself. However this is an acceptable tradeoff with regards to
// startup time performance. Indeed having this component defined as a separate
// QML file as opposed to inline makes it possible to cache its compiled form.

Component {
    id: tabComponent

    BrowserTab {
        id: browserTab
        anchors.fill: parent
        incognito: browser ? browser.incognito : false
        current: browser ? browser.tabsModel && browser.tabsModel.currentTab === this : false
        focus: current

        property var bottomEdgeHandle
        property var browser
        property var chrome
        property var chromeController
        property var contentHandlerLoader
        property var downloadDialogLoader
        property var downloadsViewLoader
        property var filePickerLoader
        property var internal
        property var recentView
        property var tabsModel
        property bool readerMode: false
        property bool isReaderable: false

        Item {
            id: contextualMenuTarget
            visible: false
        }

        webviewComponent: WebViewImpl {
            id: webviewimpl

            property BrowserTab tab
            readonly property bool current: tab.current

            currentWebview: browser ? browser.currentWebview : null
            //filePicker: filePickerLoader ? filePickerLoader.item : null

            anchors.fill: parent

            focus: true

            enabled: current && !bottomEdgeHandle.dragging && !recentView.visible && parent.focus

            Component.onCompleted: {
                var a05bdCodecScript = WebEngine.script();
                a05bdCodecScript.name = "a05bd-youtube-h264";
                a05bdCodecScript.injectionPoint = WebEngineScript.DocumentCreation;
                a05bdCodecScript.sourceUrl = Qt.resolvedUrl("assets/a05bd-youtube-h264.js");
                a05bdCodecScript.runsOnSubframes = true;
                a05bdCodecScript.worldId = WebEngineScript.MainWorld;
                userScripts.insert(a05bdCodecScript);

                var readabilityScript = WebEngine.script();
                readabilityScript.name = "readability";
                readabilityScript.injectionPoint = WebEngineScript.DocumentReady;
                readabilityScript.sourceUrl = Qt.resolvedUrl("assets/readability.js")
                readabilityScript.runsOnSubframes = true;
                readabilityScript.worldId = WebEngineScript.MainWorld;
                userScripts.insert(readabilityScript);

                var readabilityReaderableScript = WebEngine.script();
                readabilityReaderableScript.injectionPoint = WebEngineScript.DocumentReady;
                readabilityReaderableScript.sourceUrl = Qt.resolvedUrl("assets/readability-readerable.js");
                readabilityReaderableScript.runsOnSubframes = true;
                readabilityReaderableScript.worldId = WebEngineScript.MainWorld;
                userScripts.insert(readabilityReaderableScript);
            }

            onNewWindowRequested: function(request) {

                    switch (request.destination) {

                    case WebEngineView.NewViewInTab:
                        browser.newViewInNewTabRequested(request, false);
                        break;

                   case WebEngineView.NewViewInBackgroundTab:
                       browser.newViewInNewTabRequested(request, true);
                       break;

                   case WebEngineView.NewViewInWindow:
                       browser.newViewInNewWindowRequested(request, browser.incognito);
                       break;

                    // FIXME: make an actual dialog-type window, one that will
                    // close itself if the page calls window.close() and the
                    // only tab is closed. Then, use such window type only on
                    // desktop.
                    case WebEngineView.NewViewInDialog:
                        browser.newViewInNewTabRequested(request, false);
                        break;

                    }

            }

            /*
            locationBarController {
                height: chrome ? chrome.height : 0
                mode: chromeController ? chromeController.defaultMode : null
            }

            */

            //contextMenu: browser && browser.wide ? contextMenuWideComponent : contextMenuNarrowComponent
            /*
            onNewWindowRequested: {
                var newTab = browser.createTab({"request": request})
                var setCurrent = true//(request.disposition == Oxide.NewViewRequest.DispositionNewForegroundTab)
                internal.addTab(newTab, setCurrent, tabsModel.indexOf(browserTab) + 1)
                if (setCurrent) tabContainer.forceActiveFocus()
            }
*/
            onWindowCloseRequested: {
                if (tab) {
                    var i = tabsModel.indexOf(tab);
                    if (i != -1) {
                        tabsModel.remove(i);
                    }

                    // tab.close() destroys the context so add new tab before destroy if required
                    if (tabsModel.count === 0) {
                        internal.openUrlInNewTab("", true, true)
                    }

                    tab.close()
                } else if (tabsModel.count === 0) {
                    internal.openUrlInNewTab("", true, true)
                }
            }

            QtObject {
                id: webviewInternal
                property url storedUrl: ""
                property bool titleSet: false
                property string title: ""
            }

            onLoadingChanged: (loadingInfo) => {
                if (loadingInfo.status === WebEngineView.LoadSucceededStatus) {
                    chrome.findInPageMode = false
                    webviewInternal.titleSet = false
                    webviewInternal.title = title
                    readerMode = false

                    webviewimpl.runJavaScript("isProbablyReaderable(document)", function(res) {
                        isReaderable = res
                    });
                }

                if (webviewimpl.incognito) {
                    return
                }

                if (loadingInfo.status === WebEngineView.LoadSucceededStatus) {
                    webviewInternal.storedUrl = loadingInfo.url
                    // note: at this point the icon is an empty string most times, not sure why (seems to be set after this event)
                    HistoryModel.add(loadingInfo.url, title, (UrlUtils.schemeIs(icon, "image") && UrlUtils.hostIs(icon, "favicon")) ? icon.toString().substring(("image://favicon/").length) : icon)
                }

                // If the page has started, stopped, redirected, errored
                // then clear the cache for the history update
                // Otherwise if no title change has occurred the next title
                // change will be the url of the next page causing the
                // history entry to be incorrect (pad.lv/1603835)
                if (loadingInfo.status === WebEngineView.LoadFailedStatus) {
                    webviewInternal.titleSet = true
                    webviewInternal.storedUrl = ""
                }
            }
                        /*
            onTitleChanged: {
                if (!webviewInternal.titleSet && webviewInternal.storedUrl.toString()) {
                    // Record the title to avoid updating the history database
                    // every time the page dynamically updates its title.
                    // We don’t want pages that update their title every second
                    // to achieve an ugly "scrolling title" effect to flood the
                    // history database with updates.
                    webviewInternal.titleSet = true
                    if (webviewInternal.title != title) {
                        webviewInternal.title = title
                        HistoryModel.update(webviewInternal.storedUrl, title, icon)
                    }
                }
            }
            */
            onIconChanged: {

                if (webviewimpl.incognito) {
                    return
                }

                if ((icon.toString() !== '') && webviewInternal.storedUrl.toString()) {
                    HistoryModel.update(webviewInternal.storedUrl, webviewInternal.title, (UrlUtils.schemeIs(icon, "image") && UrlUtils.hostIs(icon, "favicon")) ? icon.toString().substring(("image://favicon/").length) : icon)
                }
            }
            property var certificateError
            function resetCertificateError() {
                certificateError = null
            }
            /*
            onCertificateError: {
                if (!error.isMainFrame || error.isSubresource) {
                    // Not a main frame document error, just block the content
                    // (it’s not overridable anyway).
                    return
                }
                if (internal.isCertificateErrorAllowed(error)) {
                    error.allow()
                } else {
                    certificateError = error
                    error.onCancelled.connect(webviewimpl.resetCertificateError)
                }
            }

            //onFullscreenChanged: {
            //    if (fullscreen) {
            //        fullscreenExitHintComponent.createObject(webviewimpl)
            //    }
            //}
            */
            Component {
                id: fullscreenExitHintComponent

                Rectangle {
                    id: fullscreenExitHint
                    objectName: "fullscreenExitHint"

                    anchors.centerIn: parent
                    height: units.gu(6)
                    width: Math.min(units.gu(50), parent.width - units.gu(12))
                    radius: units.gu(1)
                    color: theme.palette.normal.backgroundSecondaryText
                    opacity: 0.85

                    Behavior on opacity {
                        LomiriNumberAnimation {
                            duration: LomiriAnimation.SlowDuration
                        }
                    }
                    onOpacityChanged: {
                        if (opacity == 0.0) {
                            fullscreenExitHint.destroy()
                        }
                    }

                    // Delay showing the hint to prevent it from jumping up while the
                    // webview is being resized (https://launchpad.net/bugs/1454097).
                    visible: false
                    Timer {
                        running: true
                        interval: 250
                        onTriggered: fullscreenExitHint.visible = true
                    }

                    Label {
                        color: theme.palette.normal.background
                        font.weight: Font.Light
                        anchors.centerIn: parent
                        text: bottomEdgeHandle.enabled
                              ? i18n.tr("Swipe Up To Exit Full Screen")
                              : i18n.tr("Press ESC To Exit Full Screen")
                    }

                    Timer {
                        running: fullscreenExitHint.visible
                        interval: 2000
                        onTriggered: fullscreenExitHint.opacity = 0
                    }

                    Connections {
                        target: webviewimpl
                      //  onFullscreenChanged: {
                      //      if (!webviewimpl.fullscreen) {
                      //          fullscreenExitHint.destroy()
                      //      }
                      //  }
                    }

                    Component.onCompleted: bottomEdgeHint.forceShow = true
                    Component.onDestruction: bottomEdgeHint.forceShow = false
                }
            }
        }
        function toggleReaderMode() {
            if (browserTab.readerMode) {
                browserTab.reload()
                return
            }

            browser.currentWebview.runJavaScript("makeDomReadable()", function(r) {
                browserTab.readerMode = true
            })
        }
    }
}
