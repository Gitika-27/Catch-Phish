const pendingAllow = new Map();
const isWebUrl = (url) => /^https?:\/\//i.test(url || "");
const isExtensionUrl = (url) => (url || "").startsWith(chrome.runtime.getURL(""));
chrome.webNavigation.onBeforeNavigate.addListener((details) => {
  if (details.frameId !== 0 || !isWebUrl(details.url) || isExtensionUrl(details.url)) return;
  if (pendingAllow.get(details.tabId) === details.url) { pendingAllow.delete(details.tabId); return; }
  chrome.tabs.update(details.tabId, { url: chrome.runtime.getURL(`interstitial.html?target=${encodeURIComponent(details.url)}`) });
});
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message?.type === "allow-once" && sender.tab?.id && isWebUrl(message.url)) pendingAllow.set(sender.tab.id, message.url);
});
chrome.tabs.onRemoved.addListener((tabId) => pendingAllow.delete(tabId));
