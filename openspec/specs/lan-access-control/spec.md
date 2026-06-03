# lan-access-control Specification

## Purpose

Define lightweight LAN access control for Sharp GUI so private model and photo resources are not exposed to every device on the local network.

## Requirements

### Requirement: The system SHALL protect private LAN resources when access control is enabled

The system SHALL require owner access or an authenticated remote session before returning private model, photo, task, download, export, or workspace file resources when LAN access control is enabled.

#### Scenario: Remote unauthenticated client requests model resources
- **WHEN** a non-local unauthenticated client requests the model gallery, a model thumbnail, a model original image, a model download, a model export, or a `/files/*` workspace resource
- **THEN** the system MUST reject the request with an unauthorized response
- **AND** the system MUST NOT return private file contents or private gallery metadata

#### Scenario: Remote unauthenticated client requests photo resources
- **WHEN** a non-local unauthenticated client requests photo albums, album photos, photo thumbnails, photo originals, or photo downloads
- **THEN** the system MUST reject the request with an unauthorized response
- **AND** the system MUST NOT return private photo metadata or image bytes

#### Scenario: Authenticated remote client requests private read resources
- **WHEN** a non-local client has a valid authenticated session
- **THEN** the system SHALL allow private read workflows including model browsing, photo browsing, preview, download, and export

#### Scenario: Access control is disabled by owner choice
- **WHEN** LAN access control is disabled
- **THEN** private read workflows SHALL be reachable without the access code
- **AND** owner-only management operations MUST remain restricted to localhost owner access

### Requirement: The system SHALL provide a lightweight access-code session

The system SHALL allow a remote user to unlock the application with a deployment-level access code and SHALL maintain the unlocked state with a secure browser session cookie.

#### Scenario: Remote client submits a valid access code
- **WHEN** a non-local client submits the configured access code
- **THEN** the system SHALL create an authenticated session
- **AND** subsequent private resource requests from that browser SHALL be authorized until the session expires or is revoked

#### Scenario: Remote client submits an invalid access code
- **WHEN** a non-local client submits an invalid access code
- **THEN** the system MUST reject the login attempt
- **AND** the system MUST NOT create an authenticated session

#### Scenario: Remote client repeatedly submits invalid access codes
- **WHEN** a non-local client repeatedly submits invalid access codes
- **THEN** the system SHALL rate-limit or delay additional login attempts
- **AND** the system MUST NOT create an authenticated session

#### Scenario: Session is revoked
- **WHEN** an owner revokes existing sessions or changes the access code
- **THEN** previously issued remote sessions MUST stop authorizing private resource requests

### Requirement: The system SHALL preserve localhost owner access

The system SHALL treat localhost requests as owner requests when localhost bypass is enabled.

#### Scenario: Localhost opens the application
- **WHEN** the application is opened from localhost
- **THEN** the system SHALL allow access without requiring the access code
- **AND** the system SHALL allow owner-only management actions

#### Scenario: Request attempts to spoof owner origin
- **WHEN** a request uses forwarded IP headers, an unexpected Host header, or another client-controlled header to appear local
- **THEN** the system MUST NOT grant owner permissions from those client-controlled values
- **AND** owner-only management actions MUST remain unavailable unless the real request origin is accepted as local

#### Scenario: Remote authenticated client attempts owner-only action
- **WHEN** a non-local authenticated client attempts to modify settings, manage photo roots, delete models, restart the server, convert all models, or cancel tasks
- **THEN** the system MUST reject the action as forbidden
- **AND** the system MUST NOT perform the requested management operation

### Requirement: The system SHALL gate remote generation separately from browsing

The system SHALL keep remote generation disabled by default and SHALL allow it only when access control is enabled and remote generation is explicitly enabled by the owner.

#### Scenario: Remote generation is disabled
- **WHEN** a non-local authenticated client submits an image generation request or a photo-to-model conversion request
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT create a generation task

#### Scenario: Remote generation is enabled
- **WHEN** the owner has enabled remote generation and a non-local authenticated client submits a valid generation request
- **THEN** the system SHALL create generation tasks using the existing task queue lifecycle
- **AND** owner-only management operations MUST remain forbidden for that remote client

### Requirement: The frontend SHALL provide a clear access gate

The frontend SHALL show a lightweight access gate for unauthenticated remote clients and SHALL show the main application only after the user is authorized.

#### Scenario: Remote client is not authenticated
- **WHEN** the frontend starts and authentication status reports that the client is not authorized
- **THEN** the frontend SHALL show an access-code entry view
- **AND** the frontend MUST NOT attempt to render private gallery or photo data

#### Scenario: Login succeeds
- **WHEN** the remote user enters a valid access code
- **THEN** the frontend SHALL load the normal application data
- **AND** the user SHALL be able to use authorized browsing workflows without entering the access code again during the session

#### Scenario: Owner-only request is forbidden
- **WHEN** an authenticated remote user triggers an owner-only workflow
- **THEN** the frontend SHALL show a localized permission message
- **AND** the frontend MUST NOT present the action as successfully completed

### Requirement: Access-control UI MUST be localized and configurable by the owner

The system MUST provide localized user-facing text for access control and SHALL allow the owner to configure the access code and related LAN access settings.

#### Scenario: Owner configures access control
- **WHEN** a localhost owner enables or disables LAN access control, sets or changes the access code, session duration, session revocation, or remote generation setting
- **THEN** the system SHALL persist the updated access-control configuration
- **AND** subsequent authentication behavior SHALL follow the updated configuration

#### Scenario: Owner has not fully configured access control
- **WHEN** the localhost owner opens the app and access control is disabled or no access code has been configured
- **THEN** the frontend SHALL show a dismissible setup reminder by default on each app startup
- **AND** the owner SHALL be able to choose not to show the reminder again

#### Scenario: Language changes
- **WHEN** the application language switches between supported locales
- **THEN** access gate labels, errors, settings text, and permission messages SHALL render from locale resources

#### Scenario: Access code is not configured
- **WHEN** access control is enabled for LAN use but no access code has been configured
- **THEN** remote clients MUST NOT receive private data
- **AND** localhost owner UI SHALL provide a path to configure the access code

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
