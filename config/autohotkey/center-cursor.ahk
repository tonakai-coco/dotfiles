#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

OnForegroundChange(hWinEventHook, event, hwnd, *) {
  try {
    if WinGetMinMax(hwnd) = -1
      return
    WinGetPos(&x, &y, &w, &h, hwnd)
    MouseMove(x + w // 2, y + h // 2)
  }
}

DllCall("SetWinEventHook",
  "UInt", 0x0003,  ; EVENT_SYSTEM_FOREGROUND
  "UInt", 0x0003,
  "Ptr", 0,
  "Ptr", CallbackCreate(OnForegroundChange),
  "UInt", 0,
  "UInt", 0,
  "UInt", 0)
