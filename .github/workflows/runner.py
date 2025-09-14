      - name: Run runner.py
        env:
          TASK:    ${{ inputs.task }}
          PROFILE: ${{ inputs.profile }}
          QUERY:   ${{ inputs.query }}
        run: |
          set -e
          echo "TASK=$TASK PROFILE=$PROFILE QUERY=$QUERY"
          python runner.py --task "$TASK" --profile "$PROFILE" --query "$QUERY"

      - name: Generate cards (papers → outputs/cards.md)
        if: ${{ always() }}
        run: |
          python tools/generate_cards.py --input outputs/papers.json --out outputs/cards.md || true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: agent-test-results
          path: |
            outputs/**
            logs/**
            state/**
            *.json
          if-no-files-found: warn