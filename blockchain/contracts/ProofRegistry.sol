// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title ProofRegistry
/// @notice Stores a tamper-evident fingerprint (hash) of a discovered piece
///         of content, plus the URL it was found at, so it can later be
///         re-verified against a freshly recomputed hash.
contract ProofRegistry {
    struct Record {
        bytes32 fingerprint;
        string matchedUrl;
        uint256 timestamp;
        address submitter;
    }

    Record[] public records;

    event ProofSubmitted(uint256 indexed id, bytes32 fingerprint, string matchedUrl, address submitter);

    /// @notice Store a new proof record.
    function submitProof(bytes32 fingerprint, string calldata matchedUrl) external returns (uint256 id) {
        records.push(Record({
            fingerprint: fingerprint,
            matchedUrl: matchedUrl,
            timestamp: block.timestamp,
            submitter: msg.sender
        }));
        id = records.length - 1;
        emit ProofSubmitted(id, fingerprint, matchedUrl, msg.sender);
    }

    /// @notice Read back a stored record.
    function getRecord(uint256 id) external view returns (bytes32, string memory, uint256, address) {
        Record memory r = records[id];
        return (r.fingerprint, r.matchedUrl, r.timestamp, r.submitter);
    }

    /// @notice Re-verify: does `fingerprint` match what's on chain for `id`?
    function verify(uint256 id, bytes32 fingerprint) external view returns (bool) {
        return records[id].fingerprint == fingerprint;
    }

    function totalRecords() external view returns (uint256) {
        return records.length;
    }
}
