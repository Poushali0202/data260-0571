import React from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import NoticeForm from "./NoticeForm.jsx";
import { createNotice } from "../features/notices/noticesSlice.js";

const EMPTY = { productName: "", noticeCode: "", noticeSource: "", affectedUnits: 0, supplierId: "" };

export default function CreateRecord({ user }) {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const error = useSelector((state) => state.notices.error);

  if (!user) {
    return <p className="notice">Login required</p>;
  }

  async function handleSubmit(data) {
    const result = await dispatch(createNotice(data));
    if (createNotice.fulfilled.match(result)) {
      navigate("/");
    }
  }

  return (
    <div className="card">
      <h2>Add a grocery notice</h2>
      <NoticeForm initial={EMPTY} onSubmit={handleSubmit} submitLabel="Add notice" error={error} />
    </div>
  );
}
