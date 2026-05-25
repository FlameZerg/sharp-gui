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
