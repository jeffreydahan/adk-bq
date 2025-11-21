# Integrating Microsoft Entra ID (Azure AD) for OAuth with ADK

Switching your agent's authentication from Google's Identity Platform to Microsoft Entra ID (formerly Azure Active Directory) for OAuth involves modifying how your agent obtains and manages authentication tokens. While both systems leverage the standard OAuth 2.0 framework, the implementation details differ.

Here’s a conceptual breakdown of the necessary changes:

### 1. Application Registration in Microsoft Entra ID

The foundational step is to register your agent as an application within your Microsoft Entra ID (Azure) tenant. This process is performed in the Azure Portal, not within your Python code.

*   **Create an App Registration:** This action creates an identity for your agent application within the Microsoft ecosystem.
*   **Configure Authentication:** You will need to specify one or more **Redirect URIs**. These are callback URLs on your agent's server where Microsoft will send the user after they have successfully logged in and granted consent.
*   **Generate Client Credentials:** You will obtain a **Client ID** and generate a **Client Secret** (or configure a certificate). These credentials uniquely identify your application to Entra ID.
*   **Define API Permissions:** You must specify the necessary API permissions (scopes) that your agent requires to access protected resources on behalf of the user (e.g., Microsoft Graph API permissions like `User.Read`, custom API permissions).

### 2. Modifying the Agent's Authentication Logic

The primary code changes would occur in the authentication-related functions within your agent, such as your `get_local_dev_token` equivalent.

*   **Replace Google-Specific Token Acquisition:** The existing logic that uses `google.auth` to obtain tokens (e.g., `get_local_dev_token`) is specific to Google's identity platform. This would need to be replaced with a mechanism that interacts with Microsoft Entra ID.
*   **Utilize a Microsoft Authentication Library (MSAL):** For Python, the **Microsoft Authentication Library (MSAL)** is the standard choice. You would need to add `msal` to your project's dependencies.
*   **Implement the OAuth 2.0 Authorization Code Flow:**
    1.  **Initiate Authorization:** Your agent would construct a specially formatted URL that points to Microsoft's authorization endpoint. This URL would include your Application's Client ID, the Redirect URI, and the requested scopes.
    2.  **User Redirection:** The user's web browser would be redirected to this Microsoft authorization URL, where they would be prompted to log in to their Microsoft account and consent to your application's access.
    3.  **Handle Authorization Code Callback:** Upon successful authentication and consent, Microsoft Entra ID redirects the user back to your agent's configured Redirect URI. This redirect URL will include a temporary `authorization_code`.
    4.  **Exchange Code for Tokens:** Your agent's backend (server-side) would receive this `authorization_code`. It would then make a secure, direct request to Microsoft's token endpoint, sending the `authorization_code`, your Client ID, and Client Secret.
    5.  **Receive and Store Tokens:** Microsoft's token endpoint would validate the request and respond with an `access_token` (for accessing protected resources), a `refresh_token` (for obtaining new access tokens), and potentially an `id_token` (containing user identity information). The `access_token` is the critical component for API calls.

### 3. Adapting Token Injection and Tool Usage

Once the Microsoft Entra ID `access_token` is successfully acquired and stored (likely in the ADK `session.state`), the subsequent steps involving token injection and tool usage would be largely similar to your current implementation.

*   **Store Entra ID Token:** The acquired Microsoft `access_token` would need to be stored securely within your ADK `session.state`, similar to how your current implementation handles Google tokens.
*   **Adapt `dynamic_token_injection`:** The `dynamic_token_injection` function would be modified to search for and retrieve this **Entra ID token** from the session state. It would then inject this token into the tool's arguments in the format expected by the backend service (e.g., Application Integration) for authentication. The key used to identify the token within the session state might need adjustment.

### Summary of Conceptual Differences:

| Feature                     | Current (Google IDP)                                     | Future (Microsoft Entra ID)                               |
| :-------------------------- | :------------------------------------------------------- | :-------------------------------------------------------- |
| **Identity Setup**          | Relies on Google Cloud Project SA / End-User Accounts.   | Requires registering an application within an Entra ID tenant. |
| **Auth Library (Python)**   | `google.auth`                                            | `msal` (Microsoft Authentication Library for Python)      |
| **Token Acquisition Process** | Uses Application Default Credentials (local); Platform-managed (cloud). | Full OAuth 2.0 Authorization Code Flow via redirects to Microsoft login pages. |
| **Token Storage & Use**     | `dynamic_token_injection` finds and uses Google-issued tokens from `session.state`. | `dynamic_token_injection` would find and use Entra ID-issued tokens from `session.state`. |

In essence, the primary effort would be in implementing the correct OAuth 2.0 flow for Microsoft Entra ID to acquire the `access_token`. Once acquired, your existing token injection mechanism can be adapted to utilize the new token.
