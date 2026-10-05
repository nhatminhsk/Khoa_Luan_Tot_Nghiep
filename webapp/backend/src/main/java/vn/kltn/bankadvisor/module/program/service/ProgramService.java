package vn.kltn.bankadvisor.module.program.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.program.dto.BankProgramResponse;
import vn.kltn.bankadvisor.module.program.dto.ProgramResponse;
import vn.kltn.bankadvisor.module.program.entity.PolicyProgram;
import vn.kltn.bankadvisor.module.program.entity.ProgramParticipation;
import vn.kltn.bankadvisor.module.program.entity.ProgramRate;
import vn.kltn.bankadvisor.module.program.repository.PolicyProgramRepository;
import vn.kltn.bankadvisor.module.program.repository.ProgramParticipationRepository;
import vn.kltn.bankadvisor.module.program.repository.ProgramRateRepository;

import java.time.Clock;
import java.time.LocalDate;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class ProgramService {

    private final PolicyProgramRepository programRepository;
    private final ProgramParticipationRepository participationRepository;
    private final ProgramRateRepository rateRepository;
    private final BankService bankService;
    private final Clock clock;

    public ProgramService(PolicyProgramRepository programRepository,
                          ProgramParticipationRepository participationRepository,
                          ProgramRateRepository rateRepository, BankService bankService, Clock clock) {
        this.programRepository = programRepository;
        this.participationRepository = participationRepository;
        this.rateRepository = rateRepository;
        this.bankService = bankService;
        this.clock = clock;
    }

    public List<ProgramResponse> all() {
        return build(programRepository.findAll());
    }

    /** Các chương trình theo mã, giữ thứ tự tên. Mã không tồn tại bị bỏ qua. */
    public List<ProgramResponse> byCodes(Collection<String> codes) {
        return build(programRepository.findAllById(codes));
    }

    public List<BankProgramResponse> forBank(String ticker) {
        Bank bank = bankService.require(ticker);
        Map<String, PolicyProgram> programs = programRepository.findAll().stream()
                .collect(Collectors.toMap(PolicyProgram::getCode, Function.identity()));
        return participationRepository.findByTicker(bank.getTicker()).stream()
                .filter(p -> programs.containsKey(p.getProgramCode()))
                .map(p -> {
                    PolicyProgram program = programs.get(p.getProgramCode());
                    return new BankProgramResponse(program.getCode(), program.getName(), program.getCategory(),
                            p.isParticipates(), p.getListAsOf(), p.getSourceUrl());
                })
                .sorted(Comparator.comparing(BankProgramResponse::participates).reversed()
                        .thenComparing(BankProgramResponse::name))
                .toList();
    }

    /** Mã ngân hàng → các mã chương trình ngân hàng đó tham gia. */
    public Map<String, List<String>> participationByTicker() {
        return participationRepository.findByParticipatesTrue().stream()
                .collect(Collectors.groupingBy(ProgramParticipation::getTicker,
                        Collectors.mapping(ProgramParticipation::getProgramCode, Collectors.toList())));
    }

    private List<ProgramResponse> build(List<PolicyProgram> programs) {
        LocalDate today = LocalDate.now(clock);
        Map<String, List<ProgramParticipation>> participants = participationRepository.findByParticipatesTrue().stream()
                .collect(Collectors.groupingBy(ProgramParticipation::getProgramCode));
        Map<String, List<ProgramRate>> rates = rateRepository.findAllByOrderByProgramCodeAscValidFromAsc().stream()
                .collect(Collectors.groupingBy(ProgramRate::getProgramCode));
        return programs.stream()
                .sorted(Comparator.comparing(PolicyProgram::getName))
                .map(program -> {
                    List<ProgramParticipation> members = participants.getOrDefault(program.getCode(), List.of());
                    LocalDate listAsOf = members.stream().map(ProgramParticipation::getListAsOf)
                            .filter(Objects::nonNull).max(Comparator.naturalOrder()).orElse(null);
                    return new ProgramResponse(program.getCode(), program.getName(), program.getCategory(),
                            members.stream().map(ProgramParticipation::getTicker).sorted().toList(), listAsOf,
                            rates.getOrDefault(program.getCode(), List.of()).stream()
                                    .map(r -> new ProgramResponse.RateTerm(r.getBorrowerGroup(), r.getValidFrom(),
                                            r.getValidTo(), r.getRatePercent(), r.getSpreadMin(), r.getSpreadMax(),
                                            r.isValidOn(today)))
                                    .toList());
                })
                .toList();
    }
}
