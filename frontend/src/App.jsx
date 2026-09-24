import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import DeleteRecord from "./pages/DeleteRecord.jsx";
import { me, logout, fetchNotices, createNotice, updateNotice, deleteNotice } from "./api.js";

export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [notices, setNotices] = useState([]);

  useEffect(() => {
    me().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (user) {
      fetchNotices().then(setNotices);
    } else {
      setNotices([]);
    }
  }, [user]);

  async function handleLogout() {
    await logout();
    setUser(null);
    navigate("/");
  }

  async function addNotice(data) {
    const created = await createNotice(data);
    setNotices([...notices, created]);
    navigate("/");
  }

  async function editNotice(id, data) {
    const updated = await updateNotice(id, data);
    setNotices(notices.map((n) => (n.id === id ? updated : n)));
    navigate("/");
  }

  async function removeNotice(id) {
    await deleteNotice(id);
    setNotices(notices.filter((n) => n.id !== id));
    navigate("/");
  }

  return (
    <div className="container">
      <Navbar user={user} onLogout={handleLogout} />
      <Routes>
        <Route path="/" element={<Home user={user} notices={notices} />} />
        <Route path="/login" element={<Login onLogin={setUser} />} />
        <Route path="/create" element={<CreateRecord user={user} onAdd={addNotice} />} />
        <Route path="/update/:id" element={<UpdateRecord user={user} onUpdate={editNotice} />} />
        <Route path="/delete/:id" element={<DeleteRecord user={user} onDelete={removeNotice} />} />
      </Routes>
    </div>
  );
}
