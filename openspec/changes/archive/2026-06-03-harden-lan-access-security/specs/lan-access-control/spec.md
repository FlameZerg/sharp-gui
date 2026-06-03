## ADDED Requirements

### Requirement: The system SHALL NOT serve sensitive system files over static file routes

The system MUST NOT expose configuration, credential, certificate, or backend source files through any static file route, regardless of whether LAN access control is enabled or disabled.

#### Scenario: Client requests the runtime configuration file
- **WHEN** any client requests the runtime configuration file (containing the session signing secret and access-code hash) through a static file route
- **THEN** the system MUST reject the request without returning the file contents
- **AND** the response MUST NOT reveal the session signing secret or the access-code hash

#### Scenario: Client requests TLS private key or certificate
- **WHEN** any client requests the TLS private key or certificate file through a static file route
- **THEN** the system MUST reject the request without returning the file contents

#### Scenario: Client requests backend source files
- **WHEN** any client requests a backend source file (such as the application entry script) through a static file route
- **THEN** the system MUST reject the request without returning the file contents

#### Scenario: Access control is disabled
- **WHEN** LAN access control is disabled and a LAN client requests a sensitive system file through a static file route
- **THEN** the system MUST still reject the request
- **AND** disabling access control MUST NOT make sensitive system files reachable

### Requirement: Static file serving SHALL be limited to an explicit allowlist of served roots

The system SHALL serve files only from explicitly permitted content roots and SHALL reject any path that resolves outside those roots.

#### Scenario: Request resolves to a permitted content root
- **WHEN** a request targets a model file, model thumbnail, workspace resource, or other explicitly permitted content path
- **THEN** the system SHALL serve the file when the requester is authorized for that resource

#### Scenario: Request resolves outside permitted roots
- **WHEN** a request resolves to a path outside every permitted content root, including via relative traversal, absolute paths, or symbolic links
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT return file contents from outside the permitted roots

### Requirement: The system SHALL NOT expose a debug interface or stack traces to clients

The system SHALL run with the framework debug mode disabled by default so that runtime errors do not leak stack traces or an interactive debugger to any client.

#### Scenario: Backend raises an unhandled error
- **WHEN** a request triggers an unhandled backend error
- **THEN** the system MUST NOT return a stack trace or source code in the response
- **AND** the system MUST NOT expose an interactive debugger endpoint

#### Scenario: Operator enables diagnostics explicitly
- **WHEN** an operator explicitly enables verbose diagnostics through an environment variable on the host
- **THEN** the system MAY record detailed diagnostics to a log destination
- **AND** the system MUST NOT inject stack traces or a debugger interface into client responses

### Requirement: The bind-to-LAN setting SHALL control the actual listening address

The system SHALL bind its listening address according to the LAN bind setting so that the configured value reflects the real network exposure.

#### Scenario: LAN bind is enabled
- **WHEN** the LAN bind setting is enabled and the server starts
- **THEN** the system SHALL listen on an address reachable from other LAN devices

#### Scenario: LAN bind is disabled
- **WHEN** the LAN bind setting is disabled and the server starts
- **THEN** the system SHALL listen only on the loopback address
- **AND** other LAN devices MUST NOT be able to connect to the server

#### Scenario: Owner changes the LAN bind setting
- **WHEN** a localhost owner changes the LAN bind setting
- **THEN** the system SHALL persist the setting
- **AND** the frontend SHALL inform the owner that a restart is required for the change to take effect

### Requirement: The system SHALL warn about reverse-proxy owner misattribution and HTTP exposure

The system SHALL make the owner aware that fronting the server with a local reverse proxy can cause all requests to be treated as owner, and SHALL surface a localized warning when access codes are submitted over an unencrypted connection.

#### Scenario: Server is started behind a local reverse proxy
- **WHEN** the server is deployed behind a local reverse proxy that causes all requests to originate from the loopback address
- **THEN** the system documentation and startup diagnostics SHALL warn that all clients may be treated as owner
- **AND** the owner SHALL be able to disable localhost bypass so that all access requires the access code

#### Scenario: Access code is used over an unencrypted connection
- **WHEN** the application is served over an unencrypted (HTTP) connection and the access-control login flow is shown
- **THEN** the frontend SHALL show a localized warning that the access code is transmitted without encryption
- **AND** the warning text SHALL be maintained in both English and Chinese locale resources
