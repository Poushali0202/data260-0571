import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import Navbar from "./components/Navbar.jsx";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import { me, logout } from "./api.js";
import { fetchNotices, clearNotices } from "./features/notices/noticesSlice.js";

export default function App() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [user, setUser] = useState(null);

  useEffect(() => {
    me().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (user) {
      dispatch(fetchNotices());
    } else {
      dispatch(clearNotices());
    }
  }, [user, dispatch]);

  async function handleLogout() {
    await logout();
    setUser(null);
    navigate("/");
  }

  return (
    <div className="container">
      <Navbar user={user} onLogout={handleLogout} />
      <Routes>
        <Route path="/" element={<Home user={user} />} />
        <Route path="/login" element={<Login onLogin={setUser} />} />
        <Route path="/create" element={<CreateRecord user={user} />} />
        <Route path="/update/:id" element={<UpdateRecord user={user} />} />
      </Routes>
    </div>
  );
}
