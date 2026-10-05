"use client";

import { Chip, Link as MuiLink, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { IconCheck, IconX } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { bankRepository } from "@/repositories/bank.repository";
import { formatDate } from "@/utils/format";
import { PROGRAM_CATEGORY_LABEL } from "@/utils/labels";

export function ProgramsPanel({ ticker }: { ticker: string }) {
  const query = useQuery({ queryKey: queryKeys.bankPrograms(ticker), queryFn: () => bankRepository.programs(ticker) });

  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data) return <LoadingBlock height={320} />;

  return (
    <SectionCard
      title="Chương trình tín dụng chính sách"
      subtitle="Ngân hàng có trong danh sách tham gia hay không, theo văn bản NHNN và báo chí. Số giải ngân theo từng ngân hàng không được công bố."
      flush
    >
      {query.data.length === 0 ? (
        <EmptyState title="Chưa có dữ liệu chương trình" />
      ) : (
        <TableContainer>
          <Table size="small" aria-label="Việc tham gia chương trình tín dụng chính sách">
            <TableHead>
              <TableRow>
                <TableCell>Chương trình</TableCell>
                <TableCell>Lĩnh vực</TableCell>
                <TableCell>Tham gia</TableCell>
                <TableCell>Danh sách ngày</TableCell>
                <TableCell>Nguồn</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {query.data.map((program) => (
                <TableRow key={program.code} hover>
                  <TableCell sx={{ fontWeight: 500 }}>{program.name}</TableCell>
                  <TableCell>{PROGRAM_CATEGORY_LABEL[program.category]}</TableCell>
                  <TableCell>
                    {program.participates ? (
                      <Chip size="small" color="success" variant="outlined" icon={<IconCheck size={14} />} label="Có" />
                    ) : (
                      <Chip size="small" variant="outlined" icon={<IconX size={14} />} label="Không" />
                    )}
                  </TableCell>
                  <TableCell>{formatDate(program.listAsOf)}</TableCell>
                  <TableCell>
                    {program.sourceUrl ? (
                      <MuiLink href={program.sourceUrl} target="_blank" rel="noopener noreferrer">
                        Xem
                      </MuiLink>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        —
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </SectionCard>
  );
}
