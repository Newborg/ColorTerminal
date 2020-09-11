# ColorTerminal
Serial terminal reader with text coloring

## Features
- Color lines based on regex
- Simple search
- Always-on timestamps
- Always-on log to file
- Rename saved log file directly in main view

## Keyboard shortcuts
- Open search: **Ctrl-f**
- Close search: **Escape**
- Next search result: **Enter** or **Page Down**
- Previous search result: **Page Up**
- Go to end [tail] (autoscroll): **End** or **Alt-e**

---
## Issues and debugging

### Input from COM detected as mouse movement

https://stackoverflow.com/questions/9226082/device-misdetected-as-serial-mouse

Solutions from stackoverslow:
> Location: HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\sermouse  
> Key: Start  
> Value: 3
>
> * 0 Boot (loaded by kernel loader). Components of the driver stack for the boot (startup) volume must be loaded by the kernel loader.
> * 1 System (loaded by I/O subsystem). Specifies that the driver is loaded at kernel initialization.
> * 2 Automatic (loaded by Service Control Manager). Specifies that the service is loaded or started automatically.
> * 3 Manual. Specifies that the service does not start until the user starts it manually, such as by using Device Manager.
> * 4 Disabled. Specifies that the service should not be started.

> I also encountered this problem, fixed it by disabling "serial enumerator" in the advanced properties of the FTDI driver (properties of COM ports in Device Manager). This is described in http://www.ftdichip.com/Support/Documents/AppNotes/AN_107_AdvancedDriverOptions_AN_000073.pdf.
