    # SigmaOS-bluetooth-tool

    Bluetooth pairing CLI/GUI (blueberry/blueferry)

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/blueberry
- https://github.com/erikkb/blueferry

    ## Design principles applied
    - **Plan Before Act**
- **Separation of Concerns**
- **Defensive Programming**
- **Fail-Fast**
- **KISS**
- **DRY**

    ## Usage
    Verbs: `scan-plan, devices, pair-plan, connect-plan`

    ```
    $ sigma-bluetooth scan-plan scan.txt --adapter hci0
adapter hci0: 3 device(s)
  select hci0
  scan on
$ sigma-bluetooth devices scan.txt
4C:87:5D:1A:2B:3C  Sony WH-1000XM4  rssi=-62
$ sigma-bluetooth pair-plan scan.txt 4C:87:5D:1A:2B:3C --pin 1234
$ sigma-bluetooth connect-plan scan.txt 4C:87:5D:1A:2B:3C --paired 4C:87:5D:1A:2B:3C

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
