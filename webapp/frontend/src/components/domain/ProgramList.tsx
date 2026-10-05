"use client";

import { Box, Chip, Divider, Link as MuiLink, Stack, Typography } from "@mui/material";
import Link from "next/link";
import type { Program, ProgramRateTerm } from "@/types/api";
import { formatDate, formatNumber, formatPercent } from "@/utils/format";
import { PROGRAM_CATEGORY_LABEL } from "@/utils/labels";

function describeRate(term: ProgramRateTerm): string {
  if (term.ratePercent !== null) return formatPercent(term.ratePercent);
  if (term.spreadMin !== null && term.spreadMax !== null && term.spreadMin !== term.spreadMax)
    return `thấp hơn lãi bình quân ${formatNumber(term.spreadMin)}–${formatNumber(term.spreadMax)} điểm %`;
  if (term.spreadMin !== null) return `thấp hơn lãi bình quân ít nhất ${formatNumber(term.spreadMin)} điểm %`;
  return "chưa công bố";
}

function period(term: ProgramRateTerm): string {
  if (term.validFrom && term.validTo) return `${formatDate(term.validFrom)} – ${formatDate(term.validTo)}`;
  if (term.validFrom) return `từ ${formatDate(term.validFrom)}`;
  if (term.validTo) return `đến ${formatDate(term.validTo)}`;
  return "";
}

/** Chương trình tín dụng chính sách: lãi ưu đãi đang hiệu lực và các ngân hàng tham gia. */
export function ProgramList({ programs }: { programs: Program[] }) {
  return (
    <Stack divider={<Divider flexItem />} spacing={2}>
      {programs.map((program) => {
        const current = program.rates.filter((r) => r.current);
        return (
          <Box key={program.code}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", mb: 0.75 }} useFlexGap>
              <Typography variant="subtitle1" component="h3">
                {program.name}
              </Typography>
              <Chip size="small" label={PROGRAM_CATEGORY_LABEL[program.category]} variant="outlined" />
            </Stack>
            {current.length > 0 ? (
              <Stack spacing={0.25} sx={{ mb: 1 }}>
                {current.map((term, i) => (
                  <Typography key={i} variant="body2">
                    <Box component="span" sx={{ color: "text.secondary" }}>
                      {term.borrowerGroup}:
                    </Box>{" "}
                    <Box component="span" sx={{ fontWeight: 600 }}>
                      {describeRate(term)}
                    </Box>
                    {period(term) && (
                      <Box component="span" sx={{ color: "text.secondary" }}>
                        {" "}
                        ({period(term)})
                      </Box>
                    )}
                  </Typography>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Chưa có mức lãi ưu đãi đang hiệu lực trong dữ liệu.
              </Typography>
            )}
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
              {program.participatingTickers.length} ngân hàng tham gia
              {program.listAsOf ? ` (danh sách ngày ${formatDate(program.listAsOf)})` : ""}
            </Typography>
            <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
              {program.participatingTickers.map((ticker) => (
                <Chip key={ticker} size="small" label={ticker} component={Link} href={`/banks/${ticker}`} clickable />
              ))}
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}

export function ProgramSourceLink({ href }: { href: string | null }) {
  if (!href) return null;
  return (
    <MuiLink href={href} target="_blank" rel="noopener noreferrer" variant="caption">
      Nguồn
    </MuiLink>
  );
}
