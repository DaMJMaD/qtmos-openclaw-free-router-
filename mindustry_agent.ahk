#Requires AutoHotkey v2.0
#SingleInstance Force

SendMode "Input"
SetKeyDelay -1, -1

mindustryWin := "ahk_exe Mindustry.exe"

; ================= TUNING =================
walkToOreTime := 1200   ; time to walk onto copper
mineWaitTime  := 3000   ; time to let mining run
walkBackTime  := 1200
maxCycles     := 5

; ================= STATE =================
global botOn := false
global step := 0
global cycle := 0

; ================= HOTKEYS =================
F8::ToggleBot()
F12::ExitApp   ; EMERGENCY STOP

ToggleBot() {
    global botOn, step, cycle
    botOn := !botOn

    if botOn {
        step := 0
        cycle := 0
        SetTimer BotTick, 100
        ToolTip "MINER ON"
    } else {
        SetTimer BotTick, 0
        ToolTip "MINER OFF"
        Send "{LCtrl up}{w up}{s up}"
    }
    SetTimer () => ToolTip(), -1200
}

; ================= BOT LOOP =================
BotTick() {
    global botOn, step, cycle
    global walkToOreTime, mineWaitTime, walkBackTime, maxCycles

    if !botOn
        return

    if !WinExist(mindustryWin)
        return

    WinActivate mindustryWin

    switch step {

        case 0: ; take control
            Send "{LCtrl down}"
            Sleep 80
            step := 1
            return

        case 1: ; walk onto ore
            Send "{w down}"
            SetTimer StopWalkToOre, -walkToOreTime
            step := 2
            return

        case 2: ; waiting
            return

        case 3: ; start mining (SINGLE CLICK)
            Click
            SetTimer StopMiningWait, -mineWaitTime
            step := 4
            return

        case 4: ; waiting
            return

        case 5: ; walk back to core
            Send "{s down}"
            SetTimer StopWalkBack, -walkBackTime
            step := 6
            return

        case 6: ; finish cycle
            cycle++
            if cycle >= maxCycles {
                botOn := false
                SetTimer BotTick, 0
                Send "{LCtrl up}{w up}{s up}"
                ToolTip "MINING DONE"
                SetTimer () => ToolTip(), -1500
                return
            }
            step := 1
            return
    }
}

StopWalkToOre() {
    global step
    Send "{w up}"
    step := 3
}

StopMiningWait() {
    global step
    step := 5
}

StopWalkBack() {
    global step
    Send "{s up}"
    step := 6
}
