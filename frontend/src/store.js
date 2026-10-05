import { configureStore } from "@reduxjs/toolkit";
import noticesReducer from "./features/notices/noticesSlice.js";

export const store = configureStore({
  reducer: { notices: noticesReducer },
});
