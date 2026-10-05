import React, { useEffect, useState } from "react";
import { fetchSuppliers } from "../api.js";

export default function NoticeForm({ initial, onSubmit, submitLabel, error }) {
  const [form, setForm] = useState(initial);
  const [suppliers, setSuppliers] = useState([]);

  useEffect(() => {
    setForm(initial);
  }, [initial]);

  useEffect(() => {
    fetchSuppliers().then(setSuppliers).catch(() => setSuppliers([]));
  }, []);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({ ...form, affectedUnits: Number(form.affectedUnits), supplierId: Number(form.supplierId) });
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <p className="error">{error}</p>}
      <label>
        Product name
        <input value={form.productName} onChange={set("productName")} required />
      </label>
      <label>
        Notice code (RN-000000)
        <input value={form.noticeCode} onChange={set("noticeCode")} required />
      </label>
      <label>
        Source
        <input value={form.noticeSource} onChange={set("noticeSource")} required />
      </label>
      <label>
        Affected units
        <input type="number" min="0" value={form.affectedUnits} onChange={set("affectedUnits")} required />
      </label>
      <label>
        Supplier
        <select value={form.supplierId} onChange={set("supplierId")} required>
          <option value="">Choose a supplier</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>{s.id} - {s.name}</option>
          ))}
        </select>
      </label>
      <button type="submit">{submitLabel}</button>
    </form>
  );
}
