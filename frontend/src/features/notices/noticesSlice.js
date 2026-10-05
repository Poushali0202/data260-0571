import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api from "../../api.js";

function message(error) {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join("; ");
  return detail || error.message;
}

export const fetchNotices = createAsyncThunk("notices/fetch", async (_, { rejectWithValue }) => {
  try {
    const res = await api.get("/api/notices", { params: { page: 1, page_size: 50 } });
    return res.data;
  } catch (error) {
    return rejectWithValue(message(error));
  }
});

export const createNotice = createAsyncThunk("notices/create", async (data, { rejectWithValue }) => {
  try {
    const res = await api.post("/api/notices", data);
    return res.data;
  } catch (error) {
    return rejectWithValue(message(error));
  }
});

export const updateNotice = createAsyncThunk("notices/update", async ({ id, data }, { rejectWithValue }) => {
  try {
    const res = await api.put(`/api/notices/${id}`, data);
    return res.data;
  } catch (error) {
    return rejectWithValue(message(error));
  }
});

export const deleteNotice = createAsyncThunk("notices/delete", async (id, { rejectWithValue }) => {
  try {
    await api.delete(`/api/notices/${id}`);
    return id;
  } catch (error) {
    return rejectWithValue(message(error));
  }
});

const noticesSlice = createSlice({
  name: "notices",
  initialState: { items: [], status: "idle", error: null },
  reducers: {
    clearNotices(state) {
      state.items = [];
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotices.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchNotices.fulfilled, (state, action) => {
        state.status = "ready";
        state.items = action.payload;
      })
      .addCase(createNotice.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
        state.error = null;
      })
      .addCase(updateNotice.fulfilled, (state, action) => {
        state.items = state.items.map((n) => (n.id === action.payload.id ? action.payload : n));
        state.error = null;
      })
      .addCase(deleteNotice.fulfilled, (state, action) => {
        state.items = state.items.filter((n) => n.id !== action.payload);
        state.error = null;
      })
      .addMatcher(
        (action) => action.type.startsWith("notices/") && action.type.endsWith("/rejected"),
        (state, action) => {
          state.status = "error";
          state.error = action.payload || action.error.message;
        }
      );
  },
});

export const { clearNotices } = noticesSlice.actions;
export default noticesSlice.reducer;
