"""GraphQL queries and mutations for Pipefy portals (Interfaces schema)."""

from __future__ import annotations

from gql import gql

LIST_PORTALS_QUERY = gql(
    """
    query ListPortals(
        $org_uuid: ID!
        $filterBySubType: InterfaceSubTypeFilter!
        $searchTerm: String
    ) {
        interfaces(
            org_uuid: $org_uuid
            filterBySubType: $filterBySubType
            searchTerm: $searchTerm
        ) {
            edges {
                node {
                    id
                    name
                    visibility
                    subType
                }
            }
        }
    }
    """
)

GET_PORTAL_QUERY = gql(
    """
    query GetPortal($uuid: ID!) {
        portalInterface(uuid: $uuid) {
            id
            name
            visibility
            published
            pages {
                id
                title
                layout
                elements {
                    id
                    type
                    metadata
                    editable
                    dataSources {
                        id
                        name
                        filters
                        repoId
                        repoName
                        repoType
                        fieldKeys
                    }
                }
            }
            subPortals {
                id
                name
                published
            }
        }
    }
    """
)

LIST_INTERFACES_QUERY = gql(
    """
    query ListInterfaces(
        $org_uuid: ID!
        $filterBySubType: InterfaceSubTypeFilter!
        $searchTerm: String
        $first: Int
        $after: String
    ) {
        interfaces(
            org_uuid: $org_uuid
            filterBySubType: $filterBySubType
            searchTerm: $searchTerm
            first: $first
            after: $after
        ) {
            edges {
                node {
                    id
                    name
                    visibility
                    contentModeHtml
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """
)

GET_HTML_INTERFACE_QUERY = gql(
    """
    query GetHtmlInterface($uuid: ID!) {
        interface(uuid: $uuid) {
            id
            name
            visibility
            contentModeHtml
            pages {
                id
                title
                elements {
                    id
                    type
                    metadata
                    editable
                    dataSources {
                        id
                        name
                        filters
                        repoId
                        repoName
                        repoType
                        fieldKeys
                    }
                    htmlDocument {
                        content
                        contentHash
                        createdAt
                    }
                }
            }
        }
    }
    """
)

# The schema offers `repos` for the deprecated `interfaceRepos`, but the API answers `repos` with an error.
LIST_INTERFACE_REPOS_QUERY = gql(
    """
    query ListInterfaceRepos(
        $orgId: ID!
        $interfaceUuid: ID
        $repoName: String
        $first: Int
        $after: String
    ) {
        interfaceRepos(
            orgId: $orgId
            interfaceUuid: $interfaceUuid
            repoName: $repoName
            first: $first
            after: $after
        ) {
            edges {
                node {
                    id
                    uuid
                    suid
                    name
                    type
                    icon
                    color
                    noun
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """
)

GET_INTERFACE_REPO_FIELDS_QUERY = gql(
    """
    query GetInterfaceRepoFields($repoId: ID!, $interfaceId: ID) {
        interfacesRepoStructure(repoId: $repoId, interfaceId: $interfaceId) {
            fields {
                id
                uuid
                label
                type
                phaseId
                archived
                required
                options
                description
                helpText
                connectedRepoId
            }
        }
    }
    """
)

GET_INTERFACE_HTML_GUIDELINES_QUERY = gql(
    """
    query GetInterfaceHtmlGuidelines($includeDesignSystem: Boolean!) {
        interfaceHtmlGuidelines {
            allowedAttributePrefixes
            allowedDataAttributes
            allowedDataPfyAttributes
            allowedPlainAttributes
            allowedTags
            authoringNotes
            cssRules {
                code
                message
                subject
            }
            dataPfyVocabulary {
                attribute
                purpose
                valueFormat
            }
            designSystem @include(if: $includeDesignSystem)
            errorCodes {
                code
                description
            }
            filters {
                description
                example
                fixedColumnNames
                knownOperators {
                    filterType
                    operators
                }
            }
            forbiddenAttributes {
                code
                message
                subject
            }
            forbiddenTags {
                code
                message
                subject
            }
            linkAttributes
            maxAttributesPerElement
            maxContentBytes
            maxNestingDepth
            urlRule
        }
    }
    """
)

CREATE_INTERFACE_MUTATION = gql(
    """
    mutation CreateInterface($input: InterfaceCreateMutationInput!) {
        createInterface(input: $input) {
            interface {
                id
                name
                visibility
                contentModeHtml
                pages {
                    id
                    title
                    elements {
                        id
                        type
                    }
                }
            }
            success
        }
    }
    """
)

FIND_OR_CREATE_PORTAL_MUTATION = gql(
    """
    mutation FindOrCreatePortal($input: InterfaceCreateByTemplateMutationInput!) {
        findOrCreateInterfaceByTemplate(input: $input) {
            interface {
                id
                name
                visibility
                subType
            }
        }
    }
    """
)

UPDATE_INTERFACE_MUTATION = gql(
    """
    mutation UpdatePortal($input: InterfaceUpdateMutationInput!) {
        updateInterface(input: $input) {
            interface {
                id
                name
                visibility
                subType
            }
        }
    }
    """
)

DELETE_INTERFACE_MUTATION = gql(
    """
    mutation DeletePortal($input: InterfaceDeleteMutationInput!) {
        deleteInterface(input: $input) {
            success
        }
    }
    """
)

CREATE_PAGE_MUTATION = gql(
    """
    mutation CreatePortalPage($input: InterfacePageCreateMutationInput!) {
        createPage(input: $input) {
            page {
                id
                title
                elements {
                    id
                    type
                }
            }
        }
    }
    """
)

UPDATE_PAGE_MUTATION = gql(
    """
    mutation UpdatePortalPage($input: InterfacePageUpdateMutationInput!) {
        updatePage(input: $input) {
            page {
                id
                title
                elements {
                    id
                    type
                }
            }
        }
    }
    """
)

DELETE_PAGE_MUTATION = gql(
    """
    mutation DeletePortalPage($input: InterfacePageDeleteMutationInput!) {
        deletePage(input: $input) {
            success
        }
    }
    """
)

SORT_PAGES_MUTATION = gql(
    """
    mutation SortPortalPages($input: InterfacePageSortMutationInput!) {
        sortPages(input: $input) {
            success
        }
    }
    """
)

UPDATE_PAGE_LAYOUT_MUTATION = gql(
    """
    mutation UpdatePortalPageLayout($input: InterfacePageLayoutUpdateMutationInput!) {
        updatePageLayout(input: $input) {
            success
        }
    }
    """
)

CREATE_ELEMENT_MUTATION = gql(
    """
    mutation CreatePortalElement($input: InterfacePageElementCreateMutationInput!) {
        createElement(input: $input) {
            element {
                id
                type
                metadata
            }
        }
    }
    """
)

UPDATE_ELEMENT_MUTATION = gql(
    """
    mutation UpdatePortalElement($input: InterfacePageElementUpdateMutationInput!) {
        updateElement(input: $input) {
            success
        }
    }
    """
)

DELETE_ELEMENT_MUTATION = gql(
    """
    mutation DeletePortalElement($input: InterfacePageElementDeleteMutationInput!) {
        deleteElement(input: $input) {
            success
        }
    }
    """
)

WRITE_HTML_DOCUMENT_MUTATION = gql(
    """
    mutation WriteHtmlDocument($input: InterfacePageElementWriteHtmlDocumentInput!) {
        writeHtmlDocument(input: $input) {
            success
        }
    }
    """
)

DUPLICATE_ELEMENT_MUTATION = gql(
    """
    mutation DuplicatePortalElement($input: DuplicateInterfaceElementInput!) {
        duplicateElement(input: $input) {
            element {
                id
                type
                metadata
            }
        }
    }
    """
)

CREATE_SUB_PORTAL_MUTATION = gql(
    """
    mutation CreateSubPortal($input: CreateSubPortalInput!) {
        createSubPortal(input: $input) {
            subPortal {
                id
                name
            }
        }
    }
    """
)

__all__ = [
    "CREATE_ELEMENT_MUTATION",
    "CREATE_INTERFACE_MUTATION",
    "CREATE_PAGE_MUTATION",
    "CREATE_SUB_PORTAL_MUTATION",
    "DELETE_ELEMENT_MUTATION",
    "DELETE_INTERFACE_MUTATION",
    "DELETE_PAGE_MUTATION",
    "DUPLICATE_ELEMENT_MUTATION",
    "FIND_OR_CREATE_PORTAL_MUTATION",
    "GET_HTML_INTERFACE_QUERY",
    "GET_INTERFACE_HTML_GUIDELINES_QUERY",
    "GET_INTERFACE_REPO_FIELDS_QUERY",
    "GET_PORTAL_QUERY",
    "LIST_INTERFACES_QUERY",
    "LIST_INTERFACE_REPOS_QUERY",
    "LIST_PORTALS_QUERY",
    "SORT_PAGES_MUTATION",
    "UPDATE_ELEMENT_MUTATION",
    "UPDATE_INTERFACE_MUTATION",
    "UPDATE_PAGE_LAYOUT_MUTATION",
    "UPDATE_PAGE_MUTATION",
    "WRITE_HTML_DOCUMENT_MUTATION",
]
