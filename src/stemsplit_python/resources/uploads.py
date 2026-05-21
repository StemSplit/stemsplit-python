"""Two-step upload flow: presign + PUT."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stemsplit_python.models.uploads import UploadTicket

if TYPE_CHECKING:
    from stemsplit_python._transport import Transport


class UploadsResource:
    """``POST /upload`` and the streaming PUT to the resulting presigned URL."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create_ticket(
        self,
        *,
        filename: str,
        content_type: str | None = None,
    ) -> UploadTicket:
        """Request a presigned upload URL.

        The returned ticket is valid for 15 minutes. Use :attr:`UploadTicket.upload_key`
        when calling ``jobs.create``.
        """

        body = {"filename": filename}
        if content_type:
            body["contentType"] = content_type
        data = self._transport.request("POST", "/upload", json_body=body, retry_safe=True)
        return UploadTicket.model_validate(data)

    def put_bytes(
        self,
        ticket: UploadTicket,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> None:
        """PUT bytes directly to the presigned URL on object storage."""

        self._transport.put_to_presigned_url(
            ticket.upload_url,
            data,
            content_type or ticket.content_type,
            content_length=len(data),
        )

    def upload_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: str | None = None,
    ) -> UploadTicket:
        """Convenience: presign + PUT in one call."""

        ticket = self.create_ticket(filename=filename, content_type=content_type)
        self.put_bytes(ticket, data, content_type=content_type)
        return ticket


__all__ = ["UploadsResource"]
