"""Property-based tests for Wizard Step Data Persistence (Property 7).

Verifies that wizard step data persists correctly through round-trip operations:
- Submit step data (PUT), then retrieve it (GET) — data is identical
- Any step number (1–8) preserves data without loss
- Complex nested data structures survive the persistence round-trip
- Navigating away (retrieving a different step) and returning preserves original data

**Validates: Requirements 4.2, 4.3, 4.6**

# Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.schemas.wizard import STEP_SECTION_MAP, VALID_STEPS, StepDataSave


# =============================================================================
# In-memory wizard step storage simulating the DB round-trip
# =============================================================================


class InMemoryWizardStore:
    """In-memory storage that mirrors the wizard endpoint persistence logic.

    Simulates the behavior of:
      - PUT /projects/{id}/steps/{step}: stores step data into TOR sections
      - GET /projects/{id}/steps/{step}: retrieves step data from TOR sections

    This avoids needing a real DB while testing the core persistence property:
    data submitted equals data retrieved.
    """

    def __init__(self) -> None:
        # Storage: {project_id: {section_key: content, "sub_key:parent.sub": content}}
        self._sections: dict[uuid.UUID, dict[str, str]] = {}
        # Track current_step per project
        self._current_step: dict[uuid.UUID, int] = {}

    def save_step_data(
        self, project_id: uuid.UUID, step: int, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist step data, mirroring the wizard PUT endpoint logic."""
        if step not in VALID_STEPS:
            raise ValueError(f"Invalid step: {step}")

        if project_id not in self._sections:
            self._sections[project_id] = {}
            self._current_step[project_id] = 1

        section_keys = STEP_SECTION_MAP.get(step, [])

        # Store data keyed by section_key (same logic as wizard.py save_step_data)
        for section_key in section_keys:
            section_content = data.get(section_key, "")
            if isinstance(section_content, dict):
                section_content = json.dumps(section_content, ensure_ascii=False)
            elif not isinstance(section_content, str):
                section_content = str(section_content) if section_content else ""
            self._sections[project_id][section_key] = section_content

        # Handle sub-keys (e.g., "s4.1", "s4.2")
        for key, value in data.items():
            if "." in key:
                parts = key.split(".", 1)
                parent_key = f"s{parts[0]}" if not parts[0].startswith("s") else parts[0]
                sub_key = parts[1] if len(parts) > 1 else None
                if sub_key:
                    storage_key = f"{parent_key}.{sub_key}"
                    sub_content = value
                    if isinstance(sub_content, dict):
                        sub_content = json.dumps(sub_content, ensure_ascii=False)
                    elif not isinstance(sub_content, str):
                        sub_content = str(sub_content) if sub_content else ""
                    self._sections[project_id][storage_key] = sub_content

        # Advance current_step
        current = self._current_step[project_id]
        if step >= current:
            self._current_step[project_id] = min(step + 1, 8)

        return {"step": step, "sections_updated": len(data)}

    def get_step_data(
        self, project_id: uuid.UUID, step: int
    ) -> dict[str, str]:
        """Retrieve step data, mirroring the wizard GET endpoint logic."""
        if step not in VALID_STEPS:
            raise ValueError(f"Invalid step: {step}")

        if project_id not in self._sections:
            return {}

        section_keys = STEP_SECTION_MAP.get(step, [])
        result: dict[str, str] = {}

        # Retrieve main section keys
        for section_key in section_keys:
            if section_key in self._sections[project_id]:
                result[section_key] = self._sections[project_id][section_key]

        # Retrieve sub-keys belonging to this step's sections
        for storage_key, content in self._sections[project_id].items():
            if "." in storage_key:
                parent = storage_key.split(".")[0]
                if parent in section_keys:
                    result[storage_key] = content

        return result


# =============================================================================
# Hypothesis strategies
# =============================================================================

# Steps 1–7 have associated TOR sections; step 8 is export-only
steps_with_data = st.sampled_from([1, 2, 3, 4, 5, 6, 7])

# Generate Thai and English text content
thai_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ"
        "ะัาำิีึืุูเแโใไๅๆ็่้๊๋์ํ๐๑๒๓๔๕๖๗๘๙"
    ),
    min_size=1,
    max_size=200,
)

# Simple string values (no empty strings which trigger validation error)
content_value = st.one_of(
    thai_text,
    st.text(min_size=1, max_size=200),
    st.integers(min_value=0, max_value=10_000_000_000).map(str),
)

# Nested dict values (simulating complex form data)
nested_value = st.one_of(
    content_value,
    st.dictionaries(
        keys=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        values=st.text(min_size=0, max_size=100),
        min_size=1,
        max_size=5,
    ),
)


def step_data_for_step(step: int) -> st.SearchStrategy[dict[str, Any]]:
    """Generate valid step data keyed by the section keys for a given step."""
    section_keys = STEP_SECTION_MAP.get(step, [])
    if not section_keys:
        # Step 8 has no sections; use a generic key
        return st.dictionaries(
            keys=st.just("export_format"),
            values=content_value,
            min_size=1,
            max_size=1,
        )

    # Generate data with at least one section key from this step
    return st.fixed_dictionaries(
        {key: nested_value for key in section_keys}
    )


# =============================================================================
# Property tests
# =============================================================================


@pytest.mark.property
class TestWizardStepDataPersistence:
    """Property 7: Wizard Step Data Persistence.

    For any wizard step data submitted by the user, navigating away and
    returning to that step SHALL display the same data that was submitted —
    step data is persisted and restored without loss.
    """

    @given(
        step=steps_with_data,
        data=st.data(),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
    def test_round_trip_persistence_preserves_data(
        self, step: int, data: st.DataObject
    ):
        """Data submitted via PUT is identical when retrieved via GET.

        For any step (1–7) and any valid step data, saving the data and then
        retrieving it returns the same content for each section key.

        **Validates: Requirements 4.2, 4.3, 4.6**
        """
        project_id = uuid.uuid4()
        store = InMemoryWizardStore()

        # Generate data appropriate for this step
        step_data = data.draw(step_data_for_step(step))

        # PUT: save step data
        store.save_step_data(project_id, step, step_data)

        # GET: retrieve step data
        retrieved = store.get_step_data(project_id, step)

        # Verify round-trip: each section key's content matches
        section_keys = STEP_SECTION_MAP.get(step, [])
        for section_key in section_keys:
            original = step_data.get(section_key, "")
            # The store serializes dicts to JSON strings
            if isinstance(original, dict):
                expected = json.dumps(original, ensure_ascii=False)
            elif not isinstance(original, str):
                expected = str(original) if original else ""
            else:
                expected = original

            assert section_key in retrieved, (
                f"Section key '{section_key}' not found in retrieved data "
                f"for step {step}"
            )
            assert retrieved[section_key] == expected, (
                f"Round-trip mismatch for step {step}, section '{section_key}': "
                f"submitted={expected!r}, retrieved={retrieved[section_key]!r}"
            )

    @given(
        step=steps_with_data,
        other_step=steps_with_data,
        data=st.data(),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
    def test_navigate_away_and_return_preserves_data(
        self, step: int, other_step: int, data: st.DataObject
    ):
        """Navigating to another step and returning preserves original data.

        After saving step data, accessing a different step, then returning
        to the original step still yields the same data.

        **Validates: Requirements 4.2, 4.3, 4.6**
        """
        assume(step != other_step)

        project_id = uuid.uuid4()
        store = InMemoryWizardStore()

        # Generate and save data for the target step
        step_data = data.draw(step_data_for_step(step))
        store.save_step_data(project_id, step, step_data)

        # Generate and save data for a different step (simulating navigation)
        other_data = data.draw(step_data_for_step(other_step))
        store.save_step_data(project_id, other_step, other_data)

        # Return to the original step and retrieve
        retrieved = store.get_step_data(project_id, step)

        # Shared TOR keys (e.g. s5 on steps 1 and 6, all keys on step 7) are
        # last-write-wins on the project row — only exclusive keys must survive.
        other_keys = set(STEP_SECTION_MAP.get(other_step, []))
        section_keys = [
            key
            for key in STEP_SECTION_MAP.get(step, [])
            if key not in other_keys
        ]
        for section_key in section_keys:
            original = step_data.get(section_key, "")
            if isinstance(original, dict):
                expected = json.dumps(original, ensure_ascii=False)
            elif not isinstance(original, str):
                expected = str(original) if original else ""
            else:
                expected = original

            assert section_key in retrieved, (
                f"Section key '{section_key}' lost after navigating away from "
                f"step {step} to step {other_step}"
            )
            assert retrieved[section_key] == expected, (
                f"Data corrupted after navigating away: step {step}, "
                f"section '{section_key}': expected={expected!r}, "
                f"got={retrieved[section_key]!r}"
            )

    @given(
        step=steps_with_data,
        data=st.data(),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
    def test_overwrite_preserves_latest_data(
        self, step: int, data: st.DataObject
    ):
        """Saving step data multiple times preserves only the latest version.

        For any step, saving data twice should result in the second save's
        data being what is retrieved — no stale data from the first save leaks.

        **Validates: Requirements 4.2, 4.3**
        """
        project_id = uuid.uuid4()
        store = InMemoryWizardStore()

        # First save
        first_data = data.draw(step_data_for_step(step))
        store.save_step_data(project_id, step, first_data)

        # Second save (overwrite)
        second_data = data.draw(step_data_for_step(step))
        store.save_step_data(project_id, step, second_data)

        # Retrieve should reflect the second save
        retrieved = store.get_step_data(project_id, step)

        section_keys = STEP_SECTION_MAP.get(step, [])
        for section_key in section_keys:
            original = second_data.get(section_key, "")
            if isinstance(original, dict):
                expected = json.dumps(original, ensure_ascii=False)
            elif not isinstance(original, str):
                expected = str(original) if original else ""
            else:
                expected = original

            assert retrieved[section_key] == expected, (
                f"Overwrite failed for step {step}, section '{section_key}': "
                f"expected latest={expected!r}, got={retrieved[section_key]!r}"
            )

    @given(
        step=steps_with_data,
        data=st.data(),
    )
    @settings(max_examples=100)
    # Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
    def test_sub_key_data_persistence(
        self, step: int, data: st.DataObject
    ):
        """Sub-key data (e.g., s4.1, s4.2) persists correctly.

        For steps with subsections (like Scope of Work), sub-key data
        is stored and retrieved without loss.

        **Validates: Requirements 4.2, 4.3, 4.6**
        """
        project_id = uuid.uuid4()
        store = InMemoryWizardStore()

        section_keys = STEP_SECTION_MAP.get(step, [])
        assume(len(section_keys) > 0)

        # Create data with sub-keys for the first section
        parent = section_keys[0]
        num_subs = data.draw(st.integers(min_value=1, max_value=5))
        step_data: dict[str, Any] = {}

        # Add main section content
        main_content = data.draw(content_value)
        step_data[parent] = main_content

        # Add sub-keys like "s4.1", "s4.2" etc.
        sub_key_values: dict[str, str] = {}
        for i in range(1, num_subs + 1):
            sub_key = f"{parent}.{i}"
            sub_content = data.draw(content_value)
            step_data[sub_key] = sub_content
            sub_key_values[sub_key] = sub_content

        # Save
        store.save_step_data(project_id, step, step_data)

        # Retrieve
        retrieved = store.get_step_data(project_id, step)

        # Verify main section
        if isinstance(main_content, dict):
            expected_main = json.dumps(main_content, ensure_ascii=False)
        elif not isinstance(main_content, str):
            expected_main = str(main_content) if main_content else ""
        else:
            expected_main = main_content

        assert retrieved[parent] == expected_main, (
            f"Main section content mismatch for {parent}"
        )

        # Verify sub-keys
        for sub_key, sub_content in sub_key_values.items():
            if isinstance(sub_content, dict):
                expected_sub = json.dumps(sub_content, ensure_ascii=False)
            elif not isinstance(sub_content, str):
                expected_sub = str(sub_content) if sub_content else ""
            else:
                expected_sub = sub_content

            assert sub_key in retrieved, (
                f"Sub-key '{sub_key}' not found in retrieved data"
            )
            assert retrieved[sub_key] == expected_sub, (
                f"Sub-key data mismatch for '{sub_key}': "
                f"expected={expected_sub!r}, got={retrieved[sub_key]!r}"
            )

    @given(
        data=st.data(),
    )
    @settings(max_examples=100)
    # Feature: tor-drafting-review-app, Property 7: Wizard Step Data Persistence
    def test_all_steps_independent_persistence(
        self, data: st.DataObject
    ):
        """Each step's data is independent — saving all steps preserves all data.

        Filling in all 7 data-bearing steps and then retrieving each one
        returns the correct data for that specific step without cross-contamination.

        **Validates: Requirements 4.2, 4.3, 4.6**
        """
        project_id = uuid.uuid4()
        store = InMemoryWizardStore()

        # Save data for all steps (1–7)
        saved_data: dict[int, dict[str, Any]] = {}
        for step in range(1, 8):
            step_data = data.draw(step_data_for_step(step))
            store.save_step_data(project_id, step, step_data)
            saved_data[step] = step_data

        # Verify each step using last-write-wins for shared section keys
        # (s5 lives on steps 1 and 6; step 7 writes s1–s13).
        def last_writer(section_key: str) -> int:
            writer = 1
            for candidate in range(1, 8):
                if section_key in STEP_SECTION_MAP.get(candidate, []):
                    writer = candidate
            return writer

        for step in range(1, 8):
            retrieved = store.get_step_data(project_id, step)
            section_keys = STEP_SECTION_MAP.get(step, [])

            for section_key in section_keys:
                source_step = last_writer(section_key)
                original = saved_data[source_step].get(section_key, "")
                if isinstance(original, dict):
                    expected = json.dumps(original, ensure_ascii=False)
                elif not isinstance(original, str):
                    expected = str(original) if original else ""
                else:
                    expected = original

                assert section_key in retrieved, (
                    f"Step {step} section '{section_key}' missing after "
                    f"filling all steps"
                )
                assert retrieved[section_key] == expected, (
                    f"Cross-contamination detected: step {step}, "
                    f"section '{section_key}': expected={expected!r}, "
                    f"got={retrieved[section_key]!r}"
                )
