import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import NoticeForm from "./NoticeForm.jsx";
import api from "../api.js";
import { updateNotice } from "../features/notices/noticesSlice.js";

export default function UpdateRecord({ user }) {
  const { id } = useParams();
  const noticeId = Number(id);
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const error = useSelector((state) => state.notices.error);
  const inStore = useSelector((state) => state.notices.items.find((n) => n.id === noticeId));
  const [initial, setInitial] = useState(inStore || null);

  useEffect(() => {
    if (user && !inStore) {
      api.get(`/api/notices/${noticeId}`).then((res) => setInitial(res.data)).catch(() => setInitial(null));
    }
  }, [user, inStore, noticeId]);

  if (!user) {
    return <p className="notice">Login required</p>;
  }

  async function handleSubmit(data) {
    const result = await dispatch(updateNotice({ id: noticeId, data }));
    if (updateNotice.fulfilled.match(result)) {
      navigate("/");
    }
  }

  return (
    <div className="card">
      <h2>Update notice {noticeId}</h2>
      {initial ? (
        <NoticeForm initial={initial} onSubmit={handleSubmit} submitLabel="Update notice" error={error} />
      ) : (
        <p className="notice">Notice not found.</p>
      )}
    </div>
  );
}
