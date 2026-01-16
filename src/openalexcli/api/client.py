"""OpenAlex API client with retry logic and error handling."""

from __future__ import annotations

import random
import sys
import time
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote, urlencode

import httpx


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON output."""
        result: dict[str, Any] = {"error": self.message}
        if self.status_code:
            result["status_code"] = self.status_code
        if self.suggestion:
            result["suggestion"] = self.suggestion
        result["documentation"] = "https://docs.openalex.org/"
        return result


class RateLimitError(APIError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: int | None = None):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            suggestion="Wait a moment or add your email via --email or OPENALEX_EMAIL env var for higher limits",
        )
        self.retry_after = retry_after


# Default fields to request for each entity type
DEFAULT_WORK_FIELDS = [
    "id",
    "doi",
    "title",
    "publication_year",
    "publication_date",
    "type",
    "cited_by_count",
    "open_access",
    "authorships",
    "primary_location",
    "abstract_inverted_index",
    "topics",
    "biblio",
]

DEFAULT_AUTHOR_FIELDS = [
    "id",
    "orcid",
    "display_name",
    "works_count",
    "cited_by_count",
    "summary_stats",
    "affiliations",
    "last_known_institutions",
    "topics",
]

DEFAULT_INSTITUTION_FIELDS = [
    "id",
    "ror",
    "display_name",
    "country_code",
    "type",
    "works_count",
    "cited_by_count",
    "summary_stats",
]

DEFAULT_SOURCE_FIELDS = [
    "id",
    "issn_l",
    "display_name",
    "type",
    "works_count",
    "cited_by_count",
    "is_oa",
    "summary_stats",
]

BIBTEX_WORK_FIELDS = [
    "id",
    "doi",
    "title",
    "publication_year",
    "type",
    "authorships",
    "primary_location",
    "biblio",
    "abstract_inverted_index",
]


class OpenAlexAPI:
    """Client for the OpenAlex API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(
        self,
        email: str | None = None,
        max_retries: int = 3,
        max_retry_wait: int = 60,
        status_callback: Callable[[str], None] | None = None,
    ):
        """
        Initialize the OpenAlex API client.

        Args:
            email: Email for polite pool (higher rate limits)
            max_retries: Maximum number of retries for rate-limited requests
            max_retry_wait: Maximum wait time between retries in seconds
            status_callback: Optional callback for status messages
        """
        self.email = email
        self.max_retries = max_retries
        self.max_retry_wait = max_retry_wait
        self.status_callback = status_callback
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            headers = {
                "User-Agent": "openalexcli/0.1.0 (https://github.com/mrshu/openalexcli)",
            }
            if self.email:
                headers["mailto"] = self.email
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def __enter__(self) -> "OpenAlexAPI":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _report_status(self, message: str) -> None:
        """Report status via callback or stderr."""
        if self.status_callback:
            self.status_callback(message)
        elif sys.stderr.isatty():
            print(message, file=sys.stderr)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, path, params=params)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = (
                        int(retry_after)
                        if retry_after
                        else min(2**attempt, self.max_retry_wait)
                    )
                    # Add jitter (±25%)
                    wait_time = int(wait_time * (0.75 + random.random() * 0.5))

                    if attempt < self.max_retries:
                        resume_time = datetime.now().timestamp() + wait_time
                        resume_str = datetime.fromtimestamp(resume_time).strftime(
                            "%H:%M:%S"
                        )
                        self._report_status(
                            f"Rate limited. Retry {attempt + 1}/{self.max_retries} "
                            f"in {wait_time}s (at {resume_str})..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError(retry_after=int(retry_after) if retry_after else None)

                if response.status_code == 404:
                    raise APIError(
                        message="Entity not found",
                        status_code=404,
                        suggestion="Check the ID format. OpenAlex IDs start with W (works), A (authors), I (institutions), S (sources), etc.",
                    )

                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        message = error_data.get("message", "Bad request")
                    except Exception:
                        message = "Bad request"
                    raise APIError(
                        message=message,
                        status_code=400,
                        suggestion="Check the query parameters and filter syntax",
                    )

                raise APIError(
                    message=f"API request failed: {response.status_code}",
                    status_code=response.status_code,
                )

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = min(2**attempt, self.max_retry_wait)
                    self._report_status(
                        f"Connection error. Retry {attempt + 1}/{self.max_retries} "
                        f"in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                raise APIError(
                    message=f"Connection error: {e}",
                    suggestion="Check your network connection",
                ) from e

        raise APIError(
            message=f"Request failed after {self.max_retries} retries",
        ) from last_error

    def _build_params(
        self,
        filter_str: str | None = None,
        search: str | None = None,
        sort: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
        select: list[str] | None = None,
        group_by: str | None = None,
        extra_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build query parameters for API requests."""
        params: dict[str, Any] = {}

        # Build filter string
        filters: list[str] = []
        if filter_str:
            filters.append(filter_str)
        if extra_filters:
            for key, value in extra_filters.items():
                if value is not None:
                    filters.append(f"{key}:{value}")
        if filters:
            params["filter"] = ",".join(filters)

        if search:
            params["search"] = search
        if group_by:
            # group_by doesn't work with select; sort must be 'key' or 'count'
            params["group_by"] = group_by
            if sort in ("key", "count", "count:desc", "count:asc", "key:desc", "key:asc"):
                params["sort"] = sort
            else:
                params["sort"] = "count:desc"
        else:
            if sort:
                params["sort"] = sort
            if select:
                params["select"] = ",".join(select)
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        # Add email for polite pool if available
        if self.email:
            params["mailto"] = self.email

        return params

    # -------------------------------------------------------------------------
    # Works endpoints
    # -------------------------------------------------------------------------

    def get_work(
        self,
        work_id: str,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single work by ID."""
        # Normalize ID (handle DOI, PMID, etc.)
        normalized_id = self._normalize_work_id(work_id)
        fields = select or DEFAULT_WORK_FIELDS
        params = {"select": ",".join(fields)}
        if self.email:
            params["mailto"] = self.email
        return self._request("GET", f"/works/{normalized_id}", params)

    def search_works(
        self,
        query: str | None = None,
        filter_str: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        min_citations: int | None = None,
        open_access: bool | None = None,
        work_type: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Search for works."""
        extra_filters: dict[str, Any] = {}
        if from_date:
            extra_filters["from_publication_date"] = from_date
        if to_date:
            extra_filters["to_publication_date"] = to_date
        if min_citations is not None:
            extra_filters["cited_by_count"] = f">{min_citations}"
        if open_access is True:
            extra_filters["is_oa"] = "true"
        if work_type:
            extra_filters["type"] = work_type

        params = self._build_params(
            filter_str=filter_str,
            search=query,
            sort=sort or "cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
            group_by=group_by,
            extra_filters=extra_filters,
        )
        return self._request("GET", "/works", params)

    def get_citations(
        self,
        work_id: str,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get works that cite a given work."""
        normalized_id = self._normalize_work_id(work_id)
        # Get the full OpenAlex ID first if needed
        if not normalized_id.startswith("W"):
            work = self.get_work(normalized_id, select=["id"])
            normalized_id = work["id"].replace("https://openalex.org/", "")

        params = self._build_params(
            filter_str=f"cites:{normalized_id}",
            sort="cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
        )
        return self._request("GET", "/works", params)

    def get_references(
        self,
        work_id: str,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get works cited by a given work."""
        normalized_id = self._normalize_work_id(work_id)
        # Get the full OpenAlex ID first if needed
        if not normalized_id.startswith("W"):
            work = self.get_work(normalized_id, select=["id"])
            normalized_id = work["id"].replace("https://openalex.org/", "")

        params = self._build_params(
            filter_str=f"cited_by:{normalized_id}",
            sort="cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
        )
        return self._request("GET", "/works", params)

    def _normalize_work_id(self, work_id: str) -> str:
        """Normalize work ID to OpenAlex format."""
        # Already an OpenAlex ID
        if work_id.startswith("W") or work_id.startswith("https://openalex.org/"):
            return work_id.replace("https://openalex.org/", "")

        # DOI
        if work_id.startswith("10.") or work_id.startswith("doi:"):
            doi = work_id.replace("doi:", "").replace("https://doi.org/", "")
            return f"doi:{doi}"

        # PMID
        if work_id.lower().startswith("pmid:"):
            return work_id.lower()

        # MAG ID
        if work_id.lower().startswith("mag:"):
            return work_id.lower()

        # OpenAlex URL
        if "openalex.org" in work_id:
            return work_id.split("/")[-1]

        return work_id

    # -------------------------------------------------------------------------
    # Authors endpoints
    # -------------------------------------------------------------------------

    def get_author(
        self,
        author_id: str,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single author by ID."""
        normalized_id = self._normalize_author_id(author_id)
        fields = select or DEFAULT_AUTHOR_FIELDS
        params = {"select": ",".join(fields)}
        if self.email:
            params["mailto"] = self.email
        return self._request("GET", f"/authors/{normalized_id}", params)

    def search_authors(
        self,
        query: str,
        filter_str: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Search for authors."""
        params = self._build_params(
            filter_str=filter_str,
            search=query,
            sort=sort or "cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_AUTHOR_FIELDS,
            group_by=group_by,
        )
        return self._request("GET", "/authors", params)

    def get_author_works(
        self,
        author_id: str,
        filter_str: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Get works by an author."""
        normalized_id = self._normalize_author_id(author_id)
        # Get full OpenAlex ID if needed
        if not normalized_id.startswith("A"):
            author = self.get_author(normalized_id, select=["id"])
            normalized_id = author["id"].replace("https://openalex.org/", "")

        extra_filters: dict[str, Any] = {"authorships.author.id": normalized_id}
        if from_date:
            extra_filters["from_publication_date"] = from_date
        if to_date:
            extra_filters["to_publication_date"] = to_date

        params = self._build_params(
            filter_str=filter_str,
            sort=sort or "publication_date:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
            group_by=group_by,
            extra_filters=extra_filters,
        )
        return self._request("GET", "/works", params)

    def _normalize_author_id(self, author_id: str) -> str:
        """Normalize author ID to OpenAlex format."""
        # Already an OpenAlex ID
        if author_id.startswith("A") or author_id.startswith("https://openalex.org/"):
            return author_id.replace("https://openalex.org/", "")

        # ORCID
        if "orcid.org" in author_id or author_id.startswith("0000-"):
            orcid = author_id.replace("https://orcid.org/", "").replace("orcid:", "")
            return f"orcid:{orcid}"

        return author_id

    # -------------------------------------------------------------------------
    # Institutions endpoints
    # -------------------------------------------------------------------------

    def get_institution(
        self,
        institution_id: str,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single institution by ID."""
        normalized_id = self._normalize_institution_id(institution_id)
        fields = select or DEFAULT_INSTITUTION_FIELDS
        params = {"select": ",".join(fields)}
        if self.email:
            params["mailto"] = self.email
        return self._request("GET", f"/institutions/{normalized_id}", params)

    def search_institutions(
        self,
        query: str,
        filter_str: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Search for institutions."""
        params = self._build_params(
            filter_str=filter_str,
            search=query,
            sort=sort or "cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_INSTITUTION_FIELDS,
            group_by=group_by,
        )
        return self._request("GET", "/institutions", params)

    def get_institution_works(
        self,
        institution_id: str,
        filter_str: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Get works from an institution."""
        normalized_id = self._normalize_institution_id(institution_id)
        # Get full OpenAlex ID if needed
        if not normalized_id.startswith("I"):
            inst = self.get_institution(normalized_id, select=["id"])
            normalized_id = inst["id"].replace("https://openalex.org/", "")

        extra_filters: dict[str, Any] = {
            "authorships.institutions.id": normalized_id
        }
        if from_date:
            extra_filters["from_publication_date"] = from_date
        if to_date:
            extra_filters["to_publication_date"] = to_date

        params = self._build_params(
            filter_str=filter_str,
            sort=sort or "publication_date:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
            group_by=group_by,
            extra_filters=extra_filters,
        )
        return self._request("GET", "/works", params)

    def _normalize_institution_id(self, institution_id: str) -> str:
        """Normalize institution ID to OpenAlex format."""
        # Already an OpenAlex ID
        if institution_id.startswith("I") or institution_id.startswith(
            "https://openalex.org/"
        ):
            return institution_id.replace("https://openalex.org/", "")

        # ROR
        if "ror.org" in institution_id:
            return f"ror:{institution_id.split('/')[-1]}"
        if institution_id.startswith("ror:"):
            return institution_id

        return institution_id

    # -------------------------------------------------------------------------
    # Sources endpoints
    # -------------------------------------------------------------------------

    def get_source(
        self,
        source_id: str,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single source by ID."""
        normalized_id = self._normalize_source_id(source_id)
        fields = select or DEFAULT_SOURCE_FIELDS
        params = {"select": ",".join(fields)}
        if self.email:
            params["mailto"] = self.email
        return self._request("GET", f"/sources/{normalized_id}", params)

    def search_sources(
        self,
        query: str,
        filter_str: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Search for sources."""
        params = self._build_params(
            filter_str=filter_str,
            search=query,
            sort=sort or "cited_by_count:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_SOURCE_FIELDS,
            group_by=group_by,
        )
        return self._request("GET", "/sources", params)

    def get_source_works(
        self,
        source_id: str,
        filter_str: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        sort: str | None = None,
        page: int = 1,
        per_page: int = 25,
        select: list[str] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        """Get works from a source."""
        normalized_id = self._normalize_source_id(source_id)
        # Get full OpenAlex ID if needed
        if not normalized_id.startswith("S"):
            source = self.get_source(normalized_id, select=["id"])
            normalized_id = source["id"].replace("https://openalex.org/", "")

        extra_filters: dict[str, Any] = {"primary_location.source.id": normalized_id}
        if from_date:
            extra_filters["from_publication_date"] = from_date
        if to_date:
            extra_filters["to_publication_date"] = to_date

        params = self._build_params(
            filter_str=filter_str,
            sort=sort or "publication_date:desc",
            page=page,
            per_page=per_page,
            select=select or DEFAULT_WORK_FIELDS,
            group_by=group_by,
            extra_filters=extra_filters,
        )
        return self._request("GET", "/works", params)

    def _normalize_source_id(self, source_id: str) -> str:
        """Normalize source ID to OpenAlex format."""
        # Already an OpenAlex ID
        if source_id.startswith("S") or source_id.startswith("https://openalex.org/"):
            return source_id.replace("https://openalex.org/", "")

        # ISSN
        if len(source_id) == 9 and source_id[4] == "-":
            return f"issn:{source_id}"
        if source_id.lower().startswith("issn:"):
            return source_id.lower()

        return source_id
