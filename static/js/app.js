document.addEventListener("DOMContentLoaded", () => {
  const initCombobox = (select) => {
    if (select.closest("[data-combobox-root]")) return;
    const wrap = document.createElement("div");
    wrap.className = "combobox";
    wrap.dataset.comboboxRoot = "";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add("combobox-select");
    select.tabIndex = -1;

    const input = document.createElement("input");
    input.type = "search";
    input.className = "form-input";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    if (select.id) {
      input.id = `${select.id}_search`;
      const label = document.querySelector(`label[for="${select.id}"]`);
      if (label) label.setAttribute("for", input.id);
    }
    input.placeholder = select.dataset.comboboxPlaceholder || (document.documentElement.lang === "en" ? "Type to search" : "វាយស្វែងរក");

    const list = document.createElement("ul");
    list.className = "combobox-list";
    list.hidden = true;
    list.setAttribute("role", "listbox");
    wrap.append(input, list);

    let activeIndex = -1;
    let visible = [];

    const options = () => Array.from(select.options).filter((opt) => opt.value);
    const selectedText = () => (select.value && select.selectedOptions[0] ? select.selectedOptions[0].text : "");
    const syncFromSelect = () => {
      input.value = selectedText();
    };

    const close = () => {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      activeIndex = -1;
    };

    const place = () => {
      const rect = input.getBoundingClientRect();
      list.style.position = "fixed";
      list.style.left = `${rect.left}px`;
      list.style.width = `${rect.width}px`;
      list.style.top = `${rect.bottom + 4}px`;
      list.style.maxHeight = `${Math.min(256, Math.max(window.innerHeight - rect.bottom - 12, 120))}px`;
    };

    const highlight = () => {
      list.querySelectorAll("[data-combobox-option]").forEach((el, index) => {
        el.classList.toggle("is-active", index === activeIndex);
      });
      list.querySelector(".is-active")?.scrollIntoView({ block: "nearest" });
    };

    const choose = (value) => {
      if (select.value !== value) {
        select.value = value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      syncFromSelect();
      close();
    };

    const render = (query) => {
      const needle = (query || "").trim().toLowerCase();
      visible = options().filter((opt) => {
        if (!needle) return true;
        return opt.text.toLowerCase().includes(needle) || opt.value === needle;
      });
      list.innerHTML = "";
      if (!visible.length) {
        const empty = document.createElement("li");
        empty.className = "combobox-empty";
        empty.textContent =
          document.documentElement.lang === "en" ? "No matching students." : "មិនឃើញសិស្សត្រូវនឹងការស្វែងរក។";
        list.append(empty);
        activeIndex = -1;
        return;
      }
      visible.forEach((opt) => {
        const item = document.createElement("li");
        item.className = "combobox-option";
        item.dataset.comboboxOption = opt.value;
        item.setAttribute("role", "option");
        item.textContent = opt.text;
        if (opt.value === select.value) item.classList.add("is-selected");
        item.addEventListener("mousedown", (event) => {
          event.preventDefault();
          choose(opt.value);
        });
        list.append(item);
      });
      const selected = visible.findIndex((opt) => opt.value === select.value);
      activeIndex = selected >= 0 ? selected : 0;
      highlight();
    };

    const open = (query) => {
      const filter = query !== undefined ? query : (input.value && input.value !== selectedText() ? input.value : "");
      render(filter);
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      place();
    };

    input.addEventListener("focus", () => open());
    input.addEventListener("click", () => open());
    input.addEventListener("input", () => {
      if (!input.value) {
        choose("");
        open("");
        return;
      }
      open(input.value);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (list.hidden) open();
        activeIndex = Math.min(visible.length - 1, activeIndex + 1);
        highlight();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activeIndex = Math.max(0, activeIndex - 1);
        highlight();
      } else if (event.key === "Enter" && !list.hidden && visible[activeIndex]) {
        event.preventDefault();
        choose(visible[activeIndex].value);
      } else if (event.key === "Escape") {
        close();
        syncFromSelect();
      }
    });
    input.addEventListener("blur", () => {
      window.setTimeout(() => {
        close();
        syncFromSelect();
      }, 120);
    });
    select.addEventListener("change", syncFromSelect);
    select.form?.addEventListener("reset", () => queueMicrotask(syncFromSelect));
    select.addEventListener("invalid", (event) => {
      event.preventDefault();
      input.focus();
      open();
    });
    document.addEventListener("scroll", () => { if (!list.hidden) place(); }, true);
    window.addEventListener("resize", () => { if (!list.hidden) place(); });
    syncFromSelect();
  };

  document.querySelectorAll("select[data-combobox]").forEach(initCombobox);

  const sidebar = document.querySelector("[data-sidebar]");
  const overlay = document.querySelector("[data-sidebar-overlay]");
  const openButton = document.querySelector("[data-sidebar-open]");
  const closeButton = document.querySelector("[data-sidebar-close]");

  if (sidebar && overlay) {
    const setOpen = (isOpen) => {
      sidebar.classList.toggle("-translate-x-full", !isOpen);
      overlay.classList.toggle("hidden", !isOpen);
      document.body.classList.toggle("overflow-hidden", isOpen);
    };

    openButton?.addEventListener("click", () => setOpen(true));
    closeButton?.addEventListener("click", () => setOpen(false));
    overlay.addEventListener("click", () => setOpen(false));
  }

  const openModal = (modal) => {
    if (!modal) return;
    modal.classList.add("is-open");
    document.body.classList.add("overflow-hidden");
    modal.querySelector("input, select, textarea, button")?.focus();
  };

  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.remove("is-open");
    if (!document.querySelector(".modal-overlay.is-open")) {
      document.body.classList.remove("overflow-hidden");
    }
  };

  document.querySelectorAll("[data-modal-close]").forEach((el) => {
    el.addEventListener("click", () => closeModal(el.closest("[data-modal]")));
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".modal-overlay.is-open").forEach((modal) => closeModal(modal));
  });

  const fillForm = (form, data) => {
    Object.entries(data).forEach(([name, value]) => {
      const fields = form.querySelectorAll(`[name="${name}"]`);
      if (!fields.length) return;
      fields.forEach((field) => {
        if (field.type === "checkbox") {
          if (field.value && field.value !== "on") {
            const selected = Array.isArray(value) ? value.map(String) : [];
            field.checked = selected.includes(field.value);
          } else {
            field.checked = Boolean(value);
          }
        } else if (field.type === "file") {
          field.value = "";
        } else if (value !== undefined && value !== null) {
          field.value = value;
        }
      });
    });
  };

  document.querySelectorAll("[data-resource-modals]").forEach((root) => {
    const form = root.querySelector("[data-resource-form]");
    const formModal = root.querySelector('[data-modal="form-modal"]');
    const deleteModal = root.querySelector('[data-modal="delete-modal"]');
    const deleteForm = root.querySelector("[data-delete-form]");
    const deleteName = root.querySelector("[data-delete-name]");
    const voidModal = root.querySelector('[data-modal="void-modal"]');
    const voidForm = root.querySelector("[data-void-form]");
    const voidName = root.querySelector("[data-void-name]");
    const refundModal = root.querySelector('[data-modal="refund-modal"]');
    const refundForm = root.querySelector("[data-refund-form]");
    const refundName = root.querySelector("[data-refund-name]");
    const refundAmount = root.querySelector("[data-refund-amount]");
    const titleEl = root.querySelector("[data-form-title]");
    const payloadNode = root.querySelector("script[type='application/json']");
    const payloads = payloadNode ? JSON.parse(payloadNode.textContent) : {};
    const createUrl = root.dataset.createUrl;

    const resetAdd = () => {
      if (!form) return;
      form.reset();
      form.action = createUrl;
      if (titleEl) titleEl.textContent = root.dataset.addTitle;
      form.querySelectorAll('[name="study_days"]').forEach((field) => {
        field.checked = false;
      });
      const active = form.querySelector('[name="is_active"]');
      if (active) active.checked = true;
    };

    root.querySelectorAll("[data-add-open]").forEach((button) => {
      button.addEventListener("click", () => {
        resetAdd();
        if (button.dataset.course && form?.elements.course) {
          form.elements.course.value = button.dataset.course;
        }
        const enrollmentId = new URLSearchParams(window.location.search).get("enrollment")
          || button.dataset.enrollment;
        if (enrollmentId && form?.elements.enrollment) {
          form.elements.enrollment.value = enrollmentId;
          form.elements.enrollment.dispatchEvent(new Event("change"));
        }
        openModal(formModal);
      });
    });

    root.querySelectorAll("[data-edit-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const payload = payloads[button.dataset.editId];
        if (!payload || !form) return;
        form.reset();
        form.action = payload.edit_url;
        if (titleEl) titleEl.textContent = root.dataset.editTitle;
        fillForm(form, payload);
        openModal(formModal);
      });
    });

    root.querySelectorAll("[data-delete-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const payload = payloads[button.dataset.deleteId];
        if (!payload || !deleteForm) return;
        deleteForm.action = payload.delete_url;
        if (deleteName) deleteName.textContent = payload.label || payload.name || "";
        openModal(deleteModal);
      });
    });

    root.querySelectorAll("[data-void-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const payload = payloads[button.dataset.voidId];
        if (!payload || !voidForm) return;
        voidForm.action = payload.void_url;
        if (voidName) voidName.textContent = payload.label || payload.name || "";
        openModal(voidModal);
      });
    });

    root.querySelectorAll("[data-refund-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const payload = payloads[button.dataset.refundId];
        if (!payload || !refundForm) return;
        refundForm.action = payload.refund_url;
        if (refundName) refundName.textContent = payload.name || payload.label || "";
        if (refundAmount) refundAmount.textContent = payload.total_display || "";
        openModal(refundModal);
      });
    });

    if (root.dataset.openModal === "form") {
      openModal(formModal);
      return;
    }

    if (root.dataset.openModal === "receipt") {
      const receiptModal = root.querySelector('[data-modal="receipt-modal"]');
      openModal(receiptModal);
      const clearViewParam = () => {
        const url = new URL(window.location.href);
        if (!url.searchParams.has("view") && !url.searchParams.has("print")) return;
        url.searchParams.delete("view");
        url.searchParams.delete("print");
        history.replaceState({}, "", url);
      };
      receiptModal?.querySelectorAll("[data-modal-close]").forEach((el) => {
        el.addEventListener("click", clearViewParam);
      });
      receiptModal?.querySelectorAll("[data-receipt-print]").forEach((el) => {
        el.addEventListener("click", () => window.print());
      });
      if (new URLSearchParams(window.location.search).get("print") === "1") {
        window.setTimeout(() => window.print(), 250);
      }
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("open") === "add") {
      root.querySelector("[data-add-open]")?.click();
    }
    const editId = params.get("edit");
    if (editId) {
      root.querySelector(`[data-edit-id="${editId}"]`)?.click();
    }
  });
});
