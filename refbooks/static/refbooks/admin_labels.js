/* Presentation-only corrections for the terminology Django Admin.
 * No changes to form fields, data, validation or submit handlers.
 */
(function () {
  "use strict";

  function replaceText(root, selector, before, after) {
    root.querySelectorAll(selector).forEach(function (node) {
      if (node.textContent.trim().replace(/ё/g, "е") === before.replace(/ё/g, "е")) {
        node.textContent = after;
      }
    });
  }

  function updateInline(groupId, before, after) {
    var group = document.getElementById(groupId);
    if (!group) return;
    replaceText(group, ".add-row a", before, after);
    var data = group.getAttribute("data-inline-formset");
    if (!data) return;
    try {
      var config = JSON.parse(data);
      if (config.options && typeof config.options.addText === "string" && config.options.addText.replace(/ё/g, "е") === before.replace(/ё/g, "е")) {
        config.options.addText = after;
        group.setAttribute("data-inline-formset", JSON.stringify(config));
      }
    } catch (_ignored) {
      // Ignore malformed widget metadata rather than affecting admin behavior.
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateInline(
      "versions-group",
      "Добавить ещё один Версия справочника",
      "Добавить еще одну Версию справочника"
    );
    updateInline(
      "elements-group",
      "Добавить ещё один Элемент справочника",
      "Добавить еще один Элемент справочника"
    );
    replaceText(
      document,
      "#content h1",
      "Изменить Версия справочника",
      "Изменить версию справочника"
    );

    // Only the refbook-version deletion confirmation uses this exact wording.
    if (/\/admin\/refbooks\/refbookversion\/\d+\/delete\/$/.test(location.pathname)) {
      var heading = document.querySelector("#content h1");
      if (heading && heading.textContent.trim() === "Удалить") {
        var paragraph = document.querySelector("#content > p");
        if (paragraph && paragraph.textContent.includes("удалить Версия справочника")) {
          Array.from(paragraph.childNodes).forEach(function (node) {
            if (node.nodeType === 3 && node.nodeValue.includes("удалить Версия справочника")) {
              node.nodeValue = node.nodeValue.replace(
                "удалить Версия справочника",
                "удалить версию справочника"
              );
            }
          });
        }
      }
    }
  });
})();
