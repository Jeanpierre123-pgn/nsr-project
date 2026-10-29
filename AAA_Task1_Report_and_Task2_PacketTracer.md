# RP-Tumba College AAA Security Solution

## Task 1: Explain and plan the AAA security solution

### Purpose

RP-Tumba College currently maintains separate administrator accounts on its routers and switches. This is difficult to manage consistently and makes it harder to review administrative access. AAA provides a structured way to verify administrators, control what they may do, and keep records of their activity.

### What AAA means

AAA stands for **Authentication, Authorization, and Accounting**. These are related but distinct access-control functions:

- **Authentication - who are you?** The device or AAA service verifies an administrator's identity using credentials such as an individual username and password. For example, before opening an administrative session to R1, the router checks the supplied username and password against its configured local user database or a central AAA server.
- **Authorization - what may you do?** After authentication, policy determines which services, commands, or privilege levels are permitted. For example, a network engineer may be allowed to inspect interface status, while only an authorized network administrator may enter privileged configuration mode. Privilege level 15 should be assigned only to trusted administrators who require it.
- **Accounting - what did you do?** The device records information about a session or activity, such as the account used, login and logout times, commands issued (when supported), and whether access succeeded. These records help the college investigate changes and support auditing.

Separating the three functions makes it possible to authenticate an account successfully while still restricting its permissions and recording its activity.

### AAA characteristics and college use

AAA is enabled and applied through login or service method lists on Cisco devices. A method list specifies the order of methods to use, such as consulting a central server and then using the local database if the server cannot be reached. A local fallback should be deliberately configured and tested so a server outage does not lock administrators out.

The college should use named accounts rather than shared administrator credentials, grant only the required privilege, and record administrative sessions and commands where the device and AAA service support it. Central records should use synchronized device clocks and be protected from unauthorized changes. Access to management services should be limited to a management network and use SSH rather than Telnet wherever remote access is needed.

### Local AAA and server-based AAA

| Approach | Advantages | Limitations | Suitable use |
|---|---|---|---|
| Local AAA | The device checks its own user database; it works without network access to an AAA server and is straightforward for a small lab or emergency account. | Accounts and policy must be maintained separately on each device; changes do not automatically propagate; auditing is fragmented and local storage is limited. | Initial configuration, a small isolated network, or a carefully controlled emergency fallback. |
| Server-based AAA | Multiple routers and switches can use centrally managed identities and policy; account changes are easier to apply consistently; accounting records can be collected centrally. | Access depends on server reachability, correct routing, shared secrets, and service availability; incorrect configuration can prevent logins unless a tested fallback is available. | A college network with many managed devices and a need for consistent access control and central audit records. |

For RP-Tumba College, begin by testing local AAA on the console as in Task 2. Then deploy central AAA for managed devices, keep a separate and protected local emergency account, and test both normal server authentication and fallback before relying on the service.

### Server-based AAA protocols and ports

- **RADIUS:** UDP port **1812** is used for authentication and authorization; UDP port **1813** is used for accounting. Older deployments may use UDP ports 1645 and 1646, but the registered ports 1812 and 1813 should be preferred when supported.
- **TACACS+:** TCP port **49** is used for communication with the TACACS+ server. TACACS+ separates authentication, authorization, and accounting and is commonly used for administrative access to Cisco network devices.

The college should permit only the required AAA traffic between network devices and the AAA server, use strong unique shared secrets, and protect the management network. A shared secret is not a replacement for network protection or a secure transport design.

### Role of Cisco Secure ACS

Cisco Secure Access Control Server (ACS) is a traditional centralized AAA product for managing network-device access. Network devices are registered as AAA clients, and ACS can authenticate administrator accounts, apply authorization policies, and collect accounting records. ACS supports TACACS+ and RADIUS, allowing policy to be managed centrally instead of maintaining every administrator account independently on each router and switch. TACACS+ is especially useful for detailed command authorization on network devices; RADIUS is widely used for network access authentication and accounting.

ACS may be used if it is available and supported in the college laboratory, as the assignment allows. For a new production deployment, the college should select a currently supported AAA platform and follow its vendor guidance rather than assume that a legacy ACS installation is appropriate.

### Implementation and verification plan

1. Inventory managed devices and restrict administrative access to the management network.
2. Configure and test local AAA on a router console before enabling any remote AAA dependency.
3. Configure the central server, register each network device with the matching protocol and shared secret, and create individual administrator accounts.
4. Apply named authentication, authorization, and accounting policies. Use least privilege and a local fallback where appropriate.
5. Test a valid login, an invalid account, permitted and denied privileges, accounting records, and local fallback with the AAA server unavailable.
6. Document the configuration and protect emergency credentials and central audit records.

### References

- IETF RFC 2865, *Remote Authentication Dial In User Service (RADIUS)*.
- IETF RFC 2866, *RADIUS Accounting*.
- IETF RFC 8907, *The TACACS+ Protocol*.

## Task 2: Local AAA authentication on a router console

### Topology

Use the supplied topology: one Cisco 2911 router named **R1** and one **PC0** connected with a **Console** cable (light-blue rollover cable) from PC0's RS-232 port to R1's Console port. This task uses the console and does not require IP addresses.

In Packet Tracer, place a 2911 router and a PC in the workspace, connect PC0's RS-232 port to R1's Console port with the Console cable, then open **PC0 > Desktop > Terminal** and accept the default serial settings.

### Router configuration

Enter the following commands at the R1 console. The assignment's `Admin` / `admin123` account is intentionally weak and must only be used in the isolated class exercise. Replace the sample enable secret with a strong lab-only value if your instructor permits.

```text
enable
configure terminal
hostname R1
enable secret RPTumba!2026
ip domain-name rp-tumba.local
username Admin privilege 15 secret admin123
aaa new-model
aaa authentication login CONSOLE-LOCAL local
line console 0
 login authentication CONSOLE-LOCAL
 privilege level 15
 exec-timeout 5 0
 logging synchronous
end
copy running-config startup-config
```

If Packet Tracer asks for confirmation after `copy running-config startup-config`, press Enter to accept the default destination.

To add another individual administrator, repeat this command with a unique account and password:

```text
configure terminal
username <username> privilege <0-15> secret <strong-lab-password>
end
```

### Verify local AAA

1. Run `show running-config` and check for the hostname, domain name, enable secret, local `Admin` user, AAA method list, and console line assignment.
2. The Packet Tracer 2911 IOS image used for this lab requires `privilege level 15` under `line console 0` for the console session to start at the account's configured privilege. Run `show privilege`; the authenticated `Admin` session should report privilege level 15.
3. Close or disconnect the PC0 terminal session and reconnect to the R1 console. Confirm that the router prompts for a username and password.
4. Sign in as `Admin` with the lab password `admin123`. Confirm access and run `show privilege`.
5. Sign out and confirm that an incorrect password is rejected.
6. Save the configuration with `copy running-config startup-config` if you made further changes.

The console method list uses only the router's local database, so this lab remains usable without an AAA server. Do not use the example passwords on a real network.
